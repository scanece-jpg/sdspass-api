"""
PubChem Fiziksel Özellik Çekme Scripti
========================================
Annex 6'daki tüm CAS numaraları için PubChem'den:
  - Kaynama noktası (Boiling Point)
  - Yoğunluk (Density)
  - Parlama noktası (Flash Point)
  - Moleküler ağırlık (Molecular Weight)
verisi çeker ve pubchem_props.json dosyasına kaydeder.

Kullanım:
    python scripts/fetch_pubchem_props.py

Kaldığı yerden devam eder (Ctrl+C ile durdurabilirsiniz).
"""

import os, json, re, time, sys
import urllib.request
import urllib.error

# ── Ayarlar ──────────────────────────────────────────────────────────────────
ANNEX6_DIR   = os.path.join(os.path.dirname(__file__), '..', 'data', 'annex6')
OUTPUT_FILE  = os.path.join(os.path.dirname(__file__), 'pubchem_props.json')
DELAY        = 0.22   # saniye — PubChem limiti 5 istek/sn
BATCH_SAVE   = 50     # kaç CAS sonra kaydet

# ── Yardımcı: sayı parse ─────────────────────────────────────────────────────
def _parse_num(text):
    """'231.1 °F at 760 mmHg' → float (°C'ye çevrilmiş) veya None"""
    if not text:
        return None
    text = str(text).strip()

    # °F → °C çevrim
    f_match = re.search(r'([-\d]+(?:\.\d+)?)\s*°?\s*[Ff](?:\b|$| at)', text)
    if f_match:
        try:
            return round((float(f_match.group(1)) - 32) * 5 / 9, 1)
        except Exception:
            pass

    # Direkt sayı (°C veya g/cm³ için)
    c_match = re.search(r'([-\d]+(?:\.\d+)?)', text)
    if c_match:
        try:
            return float(c_match.group(1))
        except Exception:
            pass
    return None

def _parse_density(text):
    """'0.791 g/cm3 at 20°C' → float veya None"""
    if not text:
        return None
    text = str(text)
    m = re.search(r'([\d]+(?:\.\d+)?)\s*(?:g/(?:cm[³3]|ml|mL))', text)
    if m:
        try:
            val = float(m.group(1))
            if 0.3 < val < 5.0:   # mantıklı yoğunluk aralığı
                return round(val, 3)
        except Exception:
            pass
    return None

# ── PubChem API ───────────────────────────────────────────────────────────────
def get_cid(cas):
    url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{urllib.request.quote(cas)}/cids/JSON'
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
            cids = data.get('IdentifierList', {}).get('CID', [])
            return cids[0] if cids else None
    except Exception:
        return None

def get_experimental_props(cid):
    """pug_view ile deneysel özellikleri çek"""
    url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound/{cid}/JSON?heading=Experimental+Properties'
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            return json.loads(r.read())
    except Exception:
        return None

def get_mw(cid):
    url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/MolecularWeight/JSON'
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
            props = data.get('PropertyTable', {}).get('Properties', [])
            if props:
                return float(props[0].get('MolecularWeight', 0)) or None
    except Exception:
        pass
    return None

def extract_props(pug_data):
    """pug_view JSON'dan BP, density, FP değerlerini çıkar"""
    bp = density = fp = None
    if not pug_data:
        return bp, density, fp

    def walk(node):
        nonlocal bp, density, fp
        if isinstance(node, dict):
            name = node.get('TOCHeading', '')
            info_list = node.get('Information', [])
            for info in info_list:
                val_raw = None
                # Değeri al
                for sv in info.get('Value', {}).get('StringWithMarkup', []):
                    val_raw = sv.get('String', '')
                    break
                if not val_raw:
                    num_val = info.get('Value', {}).get('Number', [])
                    if num_val:
                        val_raw = str(num_val[0])

                if val_raw:
                    nl = name.lower()
                    if 'boiling' in nl and bp is None:
                        bp = _parse_num(val_raw)
                        # BP mantıklı aralık: -200 ile 800°C
                        if bp is not None and not (-200 < bp < 800):
                            bp = None
                    elif 'flash' in nl and fp is None:
                        fp = _parse_num(val_raw)
                        if fp is not None and not (-100 < fp < 400):
                            fp = None
                    elif 'density' in nl and density is None:
                        density = _parse_density(val_raw)

            for v in node.values():
                if isinstance(v, (dict, list)):
                    walk(v)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(pug_data)
    return bp, density, fp


# ── Ana iş akışı ──────────────────────────────────────────────────────────────
def load_progress():
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_progress(data):
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_annex6_cas():
    cas_list = []
    for root, dirs, files in os.walk(ANNEX6_DIR):
        for fname in files:
            if fname.endswith('.json'):
                cas = fname.replace('.json', '')
                if cas != '-' and re.match(r'[\d]', cas):
                    cas_list.append(cas)
    return sorted(set(cas_list))

def main():
    cas_list = get_annex6_cas()
    print(f'Toplam annex6 CAS: {len(cas_list)}')

    results = load_progress()
    done    = set(results.keys())
    todo    = [c for c in cas_list if c not in done]
    print(f'Tamamlanan: {len(done)}, Kalan: {len(todo)}')

    if not todo:
        print('Tüm CAS lar işlendi! pubchem_props.json hazır.')
        return

    try:
        for i, cas in enumerate(todo, 1):
            # CID al
            cid = get_cid(cas)
            time.sleep(DELAY)

            if not cid:
                results[cas] = {'found': False}
                if i % 10 == 0:
                    print(f'  [{i}/{len(todo)}] {cas} → CID yok')
            else:
                # MW
                mw = get_mw(cid)
                time.sleep(DELAY)

                # Deneysel özellikler
                pug = get_experimental_props(cid)
                time.sleep(DELAY)

                bp, density, fp = extract_props(pug)

                results[cas] = {
                    'found':   True,
                    'cid':     cid,
                    'mw':      mw,
                    'bp':      bp,
                    'density': density,
                    'fp':      fp,
                }

                if i % 10 == 0 or bp or density or fp:
                    status = f'BP={bp}, d={density}, FP={fp}, MW={mw}'
                    print(f'  [{i}/{len(todo)}] {cas} (CID {cid}) -> {status}')

            # Periyodik kayıt
            if i % BATCH_SAVE == 0:
                save_progress(results)
                print(f'  >>> {len(results)} kayıt kaydedildi.')

    except KeyboardInterrupt:
        print('\nDurduruldu. İlerleme kaydediliyor...')

    save_progress(results)
    found   = sum(1 for v in results.values() if v.get('found'))
    has_bp  = sum(1 for v in results.values() if v.get('bp') is not None)
    has_den = sum(1 for v in results.values() if v.get('density') is not None)
    has_fp  = sum(1 for v in results.values() if v.get('fp') is not None)
    print(f'\nSonuç: {len(results)} CAS işlendi')
    print(f'  Bulunan CID: {found}')
    print(f'  BP verisi:   {has_bp}')
    print(f'  Yoğunluk:    {has_den}')
    print(f'  Parlama:     {has_fp}')
    print(f'\nDosya: {OUTPUT_FILE}')
    print('Sonraki adım: python scripts/apply_pubchem_props.py')

if __name__ == '__main__':
    main()
