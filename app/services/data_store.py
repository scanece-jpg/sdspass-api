"""
Çalışma anında yazılan verilerin kalıcılığı — GitHub'daki ayrı, gizli veri deposu.

Başlangıçta depo indirilip proje klasörüne serilir (sync_down); çalışırken yazılan
her dosya persist() ile arka planda depoya commit edilir. Böylece veriler deploy'dan
ve barındırma hizmetinden bağımsız kalır.

Ortam değişkenleri tanımlı değilse (yerel geliştirme) hiçbir şey yapmaz:
  SDSPASS_DATA_REPO    örn. scanece-jpg/sdspass-data
  SDSPASS_DATA_TOKEN   yalnızca o depoya "Contents: read & write" yetkili fine-grained token
  SDSPASS_DATA_BRANCH  varsayılan: main
"""
import base64, hashlib, io, json, os, queue, re, tarfile, threading, time
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT    = Path(__file__).resolve().parents[2]
REPO    = os.environ.get('SDSPASS_DATA_REPO', '').strip()
TOKEN   = os.environ.get('SDSPASS_DATA_TOKEN', '').strip()
BRANCH  = os.environ.get('SDSPASS_DATA_BRANCH', 'main').strip() or 'main'
ENABLED = bool(REPO and TOKEN)

# Kayıt başına bir dosya — depodaki sürüm kazanır
_TREES = ('data/echa_cl/', 'data/pubchem_cl/', 'data/phys_cache/', 'data/echa_phys/',
          'data/hesaplar/')  # danışman hesapları: firma kayıtları, üretilen / tedarikçi GBF'leri (accounts.py)
# Tek JSON sözlük — anahtar bazında birleştirilir.
# 'remote': depodaki kazanır | 'local': ana git deposundaki (elle düzenlenmiş) kazanır
_JSON_MERGE = {
    'data/echa_cl_archive.json'   : 'remote',
    'data/cameo_cache.json'       : 'remote',
    'app/services/echa_cache.json': 'remote',
    'data/substances_custom.json' : 'local',
}
# Satır bazlı metin — satırlar birleştirilir
_TEXT_UNION = ('sds-knowledge/review_rules.md', 'data/echa_changes.jsonl')

_API     = 'https://api.github.com'
_q: 'queue.Queue[str]' = queue.Queue()
_pending: set = set()
_shas: dict = {}
_lock    = threading.Lock()
_worker  = None
# /health için durum — depo adı ve token gösterilmez
_status: dict = {'indirilen': None, 'yuklenen': 0, 'son_hata': None, 'son_hata_zamani': None,
                 'son_basari_zamani': None}


def _err(msg: str) -> None:
    print(msg)
    # /health herkese açık — adres (depo adı) ve ek satırlar gösterilmez
    _status['son_hata'] = re.sub(r"\s*for url '[^']*'", '', msg.replace('[data_store] ', '')).split('\n')[0][:200]
    _status['son_hata_zamani'] = time.strftime('%Y-%m-%d %H:%M:%S')


def status() -> dict:
    """Kalıcılık durumu (tarayıcıdan /health ile kontrol için)."""
    if not ENABLED:
        return {'durum': 'KAPALI — SDSPASS_DATA_REPO / SDSPASS_DATA_TOKEN tanımlı değil; veriler her deploy\'da silinir'}
    # Hatadan sonra başarılı yükleme olduysa sorun giderilmiştir (zaman damgaları aynı biçimde → metin karşılaştırma)
    _hata, _basari = _status['son_hata_zamani'], _status['son_basari_zamani']
    if not _hata:
        durum = 'açık'
    elif _basari and _basari >= _hata:
        durum = 'açık (önceki hata giderildi — sonraki yüklemeler başarılı)'
    else:
        durum = 'açık — HATA VAR'
    return {'durum': durum, 'baslangicta_indirilen_dosya': _status['indirilen'],
            'bu_oturumda_yuklenen': _status['yuklenen'], 'bekleyen': _q.unfinished_tasks,
            'son_basarili_yukleme': _basari, 'son_hata': _status['son_hata'], 'son_hata_zamani': _hata}


def _headers() -> dict:
    return {
        'Authorization'       : f'Bearer {TOKEN}',
        'Accept'              : 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'User-Agent'          : 'sdspass-api',
    }


def _is_persisted(rel: str) -> bool:
    return rel.startswith(_TREES) or rel in _JSON_MERGE or rel in _TEXT_UNION


def _rel(path) -> str | None:
    try:
        rel = Path(path).resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return None
    return rel if _is_persisted(rel) else None


def _blob_sha(data: bytes) -> str:
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


# ── İndirme (başlangıçta) ─────────────────────────────────────────────────────

def _apply_remote(rel: str, data: bytes) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)

    if rel in _JSON_MERGE and p.exists():
        try:
            local  = json.loads(p.read_text(encoding='utf-8'))
            remote = json.loads(data.decode('utf-8'))
        except Exception as e:
            print(f'[data_store] {rel}: JSON okunamadı, yerel sürüm korunuyor — {e}')
            return
        if isinstance(local, dict) and isinstance(remote, dict):
            merged = {**local, **remote} if _JSON_MERGE[rel] == 'remote' else {**remote, **local}
            p.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
            return

    if rel in _TEXT_UNION and p.exists():
        local = p.read_text(encoding='utf-8').splitlines()
        seen  = set(local)
        extra = [l for l in data.decode('utf-8').splitlines() if l.strip() and l not in seen]
        if extra:
            p.write_text('\n'.join(local + extra) + '\n', encoding='utf-8')
        return

    p.write_bytes(data)


def sync_down() -> None:
    """Veri deposunu indir ve proje klasörüne uygula. Hata olursa yerel dosyalarla devam edilir."""
    if not ENABLED:
        print('[data_store] kapalı (SDSPASS_DATA_REPO / SDSPASS_DATA_TOKEN tanımlı değil) — yerel dosyalar kullanılıyor')
        return
    try:
        with httpx.Client(timeout=60, follow_redirects=True) as c:
            r = c.get(f'{_API}/repos/{REPO}/tarball/{quote(BRANCH)}', headers=_headers())
            if r.status_code in (404, 409):
                print(f'[data_store] {REPO}: depo boş ya da dal yok — ilk yazmada oluşturulacak')
                _status['indirilen'] = 0
                return
            r.raise_for_status()

            n = 0
            with tarfile.open(fileobj=io.BytesIO(r.content), mode='r:gz') as tar:
                for m in tar.getmembers():
                    if not m.isfile():
                        continue
                    parts = m.name.split('/', 1)          # ilk parça: owner-repo-sha/
                    if len(parts) != 2:
                        continue
                    rel = parts[1]
                    if rel.startswith('/') or '..' in rel.split('/') or not _is_persisted(rel):
                        continue
                    f = tar.extractfile(m)
                    if f is None:
                        continue
                    _apply_remote(rel, f.read())
                    n += 1

            t = c.get(f'{_API}/repos/{REPO}/git/trees/{quote(BRANCH)}',
                      params={'recursive': 1}, headers=_headers())
            if t.status_code == 200:
                _shas.update({x['path']: x['sha'] for x in t.json().get('tree', [])
                              if x.get('type') == 'blob'})

        print(f'[data_store] {REPO}: {n} dosya indirildi')
        _status['indirilen'] = n
    except Exception as e:
        _err(f'[data_store] indirme hatası — yerel dosyalarla devam: {type(e).__name__}: {e}')


# ── Yükleme (çalışırken, arka planda) ─────────────────────────────────────────

def persist(path) -> None:
    """Yazılmış bir dosyayı veri deposuna commit edilmek üzere kuyruğa al."""
    if not ENABLED:
        return
    rel = _rel(path)
    if not rel:
        print(f'[data_store] kalıcı listede olmayan yol atlandı: {path}')
        return
    with _lock:
        if rel in _pending:
            return
        _pending.add(rel)
    _ensure_worker()
    _q.put(rel)


def _ensure_worker() -> None:
    global _worker
    with _lock:
        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(target=_run, name='data_store', daemon=True)
            _worker.start()


def _run() -> None:
    with httpx.Client(timeout=30) as c:
        while True:
            rel = _q.get()
            with _lock:
                _pending.discard(rel)   # yükleme sırasında gelen yeni yazma tekrar kuyruğa girebilsin
            try:
                _upload(c, rel)
            except Exception as e:
                _err(f'[data_store] {rel} yükleme hatası: {type(e).__name__}: {e}')
            finally:
                _q.task_done()


def _upload(c: httpx.Client, rel: str) -> None:
    p = ROOT / rel
    if not p.exists():
        return
    data = p.read_bytes()
    if _shas.get(rel) == _blob_sha(data):
        return
    url = f'{_API}/repos/{REPO}/contents/{quote(rel)}'
    for _ in range(3):
        body = {'message': f'veri: {rel}', 'branch': BRANCH,
                'content': base64.b64encode(data).decode()}
        if rel in _shas:
            body['sha'] = _shas[rel]
        r = c.put(url, headers=_headers(), json=body)
        if r.status_code in (200, 201):
            _shas[rel] = r.json()['content']['sha']
            _status['yuklenen'] += 1
            _status['son_basari_zamani'] = time.strftime('%Y-%m-%d %H:%M:%S')
            return
        if r.status_code in (409, 422):           # sha eski ya da eksik → depodaki güncel sha'yı al
            g = c.get(url, headers=_headers(), params={'ref': BRANCH})
            if g.status_code == 200:
                _shas[rel] = g.json()['sha']
            else:
                _shas.pop(rel, None)
            continue
        r.raise_for_status()
    _err(f'[data_store] {rel}: 3 denemede yüklenemedi')


def flush(timeout: float = 20.0) -> None:
    """Kapanışta bekleyen yüklemelerin bitmesini (en fazla timeout sn) bekle."""
    if not ENABLED:
        return
    end = time.time() + timeout
    while _q.unfinished_tasks and time.time() < end:
        time.sleep(0.2)
    if _q.unfinished_tasks:
        print(f'[data_store] kapanışta {_q.unfinished_tasks} dosya yüklenemeden kaldı')
