"""
Danışman hesapları ve firma klasörleri.

Bir danışman (KDU / danışmanlık firması) hesabının altında çok sayıda müşteri firma bulunur:

    data/hesaplar/<hesap>/firmalar/<firma>/firma.json       Bölüm 1.3 / 1.4 bilgileri
                                           uretilen_gbf/    üretilen GBF'ler (PDF + girdiler)
                                           tedarikci_gbf/   tedarikçiden gelen GBF'ler (PDF + okunan veriler)

Klasörler ilk kayıtta otomatik açılır. Giriş sistemi yok: her hesabın gizli bir anahtarı vardır,
ortam değişkeninde tanımlanır (anahtarı olmayan hiçbir klasörü göremez):

    SDSPASS_HESAP_ANAHTARLARI = "dipol-kimya:<anahtar>[,<hesap2>:<anahtar2>]"

Anahtar üretmek için: python scripts/hesap_anahtari.py <hesap>
Veriler açık git deposuna girmez (.gitignore); gizli veri deposuna yedeklenir (data_store).
"""
import hmac, json, os, re, time
from pathlib import Path
from typing import Dict, Optional

from fastapi import APIRouter, Body, Header, HTTPException

from app.services.data_store import persist

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'data' / 'hesaplar'
_ID = re.compile(r'^[a-z0-9][a-z0-9-]{0,59}$')
_MIN_KEY = 24
# Bölüm 1.3 / 1.4 — firma kaydında tutulan alanlar
_FIELDS = ('name', 'address', 'phone', 'email', 'contact', 'emergency_tel', 'emergency_hours')
_TR = str.maketrans('çğıöşüâîûÇĞİÖŞÜÂÎÛ', 'cgiosuaiuCGIOSUAIU')


def _keys() -> Dict[str, str]:
    out = {}
    for part in os.environ.get('SDSPASS_HESAP_ANAHTARLARI', '').split(','):
        h, _, k = part.strip().partition(':')
        if _ID.match(h.strip()) and len(k.strip()) >= _MIN_KEY:
            out[h.strip()] = k.strip()
    return out


def hesap_of(authorization: Optional[str]) -> str:
    """'Bearer <anahtar>' → hesap adı; geçersizse 401."""
    key = (authorization or '').removeprefix('Bearer ').strip()
    if len(key) >= _MIN_KEY:
        for h, k in _keys().items():
            if hmac.compare_digest(k.encode(), key.encode()):
                return h
    raise HTTPException(status_code=401, detail='Hesap anahtarı geçersiz veya tanımlı değil.')


def slug(name: str) -> str:
    s = (name or '').translate(_TR).lower()
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return s[:50].strip('-') or 'firma'


def firma_dir(hesap: str, fid: str) -> Path:
    if not (_ID.match(hesap) and _ID.match(fid or '')):
        raise HTTPException(status_code=400, detail='Geçersiz firma kimliği.')
    return BASE / hesap / 'firmalar' / fid


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(path)
    persist(path)


def _read_firma(d: Path) -> Optional[dict]:
    try:
        return json.loads((d / 'firma.json').read_text(encoding='utf-8'))
    except Exception:
        return None


def _clean(body: dict) -> dict:
    return {f: str(body.get(f) or '').strip()[:300] for f in _FIELDS}


def _count(d: Path, sub: str) -> int:
    p = d / sub
    return len(list(p.glob('*.json'))) if p.is_dir() else 0


router = APIRouter(prefix='/api/v1/hesap', tags=['hesap'])


@router.get('')
def hesap_bilgi(authorization: Optional[str] = Header(None)):
    h = hesap_of(authorization)
    root = BASE / h / 'firmalar'
    return {'hesap': h, 'firma_sayisi': len([d for d in root.iterdir() if d.is_dir()]) if root.is_dir() else 0}


@router.get('/firmalar')
def firma_listesi(authorization: Optional[str] = Header(None)):
    h = hesap_of(authorization)
    root = BASE / h / 'firmalar'
    out = []
    if root.is_dir():
        for d in root.iterdir():
            f = _read_firma(d) if d.is_dir() else None
            if f:
                out.append({'id': d.name, 'name': f.get('name', ''), 'guncelleme': f.get('_guncelleme', ''),
                            'uretilen_gbf': _count(d, 'uretilen_gbf'), 'tedarikci_gbf': _count(d, 'tedarikci_gbf')})
    out.sort(key=lambda x: x['name'].translate(_TR).lower())
    return {'hesap': h, 'firmalar': out}


@router.post('/firmalar')
def firma_ekle(body: dict = Body(...), authorization: Optional[str] = Header(None)):
    h = hesap_of(authorization)
    data = _clean(body)
    if not data['name']:
        raise HTTPException(status_code=422, detail='Firma adı zorunludur.')
    root = BASE / h / 'firmalar'
    if root.is_dir():
        for d in root.iterdir():
            f = _read_firma(d) if d.is_dir() else None
            if f and slug(f.get('name', '')) == slug(data['name']):
                raise HTTPException(status_code=409, detail=f"Bu adla kayıtlı firma var: {f.get('name')} ({d.name})")
    base, fid, n = slug(data['name']), None, 1
    while True:
        fid = base if n == 1 else f'{base}-{n}'
        if not (BASE / h / 'firmalar' / fid).exists():
            break
        n += 1
    d = firma_dir(h, fid)
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    _write_json(d / 'firma.json', {**data, '_olusturma': now, '_guncelleme': now})
    return {'id': fid, **data}


@router.get('/firmalar/{fid}')
def firma_getir(fid: str, authorization: Optional[str] = Header(None)):
    h = hesap_of(authorization)
    f = _read_firma(firma_dir(h, fid))
    if f is None:
        raise HTTPException(status_code=404, detail='Firma bulunamadı.')
    return {'id': fid, **f}


@router.put('/firmalar/{fid}')
def firma_guncelle(fid: str, body: dict = Body(...), authorization: Optional[str] = Header(None)):
    h = hesap_of(authorization)
    d = firma_dir(h, fid)
    f = _read_firma(d)
    if f is None:
        raise HTTPException(status_code=404, detail='Firma bulunamadı.')
    data = _clean(body)
    if not data['name']:
        raise HTTPException(status_code=422, detail='Firma adı zorunludur.')
    f.update(data)
    f['_guncelleme'] = time.strftime('%Y-%m-%d %H:%M:%S')
    _write_json(d / 'firma.json', f)
    return {'id': fid, **f}
