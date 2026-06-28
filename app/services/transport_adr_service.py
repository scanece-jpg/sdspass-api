"""
ADR Taşımacılık Servisi
=======================
UN numarasından ADR detaylarını döndürür:
  - Kemler kodu (tehlike tanımlama numarası)
  - Tünel kısıtlama kodu
  - Sınıflandırma kodu
  - Etiket
  - Sınırlı miktar

Kaynak: ADR 2023 Tablo A
"""

import json
from pathlib import Path

_ADR_DATA = None

def _load():
    global _ADR_DATA
    if _ADR_DATA is None:
        p = Path(__file__).parent.parent.parent / 'data' / 'adr_data.json'
        if p.exists():
            with open(p, encoding='utf-8') as f:
                _ADR_DATA = json.load(f)
        else:
            _ADR_DATA = {}
    return _ADR_DATA


def get_adr_details(un_no: str, packing_group: str = 'II') -> dict:
    """
    UN numarası ve ambalaj grubundan ADR detaylarını getir.

    Returns:
        {
          un_no, name, name_tr, class, classification_code,
          kemler, tunnel_code, label,
          imdg_class, iata_class  (aynı sınıf, farklı isim)
        }
    """
    db = _load()

    # UN no formatını normalize et — "UN 3093", "un3093", "3093" hepsini kabul et
    un_key = un_no.upper().replace(' ', '').strip()
    if not un_key.startswith('UN'):
        un_key = 'UN' + un_key

    entry = db.get(un_key)
    if not entry:
        return {
            'un_no': un_key,
            'name': 'NOT FOUND',
            'name_tr': 'Bulunamadı',
            'class': '—',
            'classification_code': '—',
            'kemler': '—',
            'tunnel_code': '—',
            'label': '—',
            'found': False,
        }

    # Ambalaj grubuna göre detay
    pg = packing_group.upper().replace('PG', '').strip()
    pg_data = entry.get('packing_groups', {}).get(pg, {})

    # İç içe yapıda PG bulunamazsa ilk olanı al
    _pg_used = pg
    if not pg_data and entry.get('packing_groups'):
        _first_key = list(entry['packing_groups'].keys())[0]
        pg_data = entry['packing_groups'][_first_key]
        _pg_used = _first_key

    # Düz (flat) yapı desteği: packing_groups yoksa üst seviyeden oku.
    # Bazı kayıtlar (örn. UN3098) packing_groups dict'i taşımaz;
    # packing_group / kemler / tunnel alanları doğrudan giriş seviyesindedir.
    _has_nested = bool(entry.get('packing_groups'))
    _pg_final      = _pg_used if _has_nested else (entry.get('packing_group') or _pg_used)
    _kemler_final  = pg_data.get('kemler') if _has_nested else entry.get('kemler', '')
    _tunnel_final  = pg_data.get('tunnel') if _has_nested else entry.get('tunnel', '—')
    # Her iki yapıda da pg_data boşsa üst seviyeye düş (ek güvence)
    if _kemler_final is None:
        _kemler_final = entry.get('kemler', '')
    if _tunnel_final is None:
        _tunnel_final = entry.get('tunnel', '—')

    return {
        'un_no':               un_key,
        'name':                entry.get('name', ''),
        'name_tr':             entry.get('name_tr', ''),
        'class':               entry.get('class', '—'),
        'classification_code': pg_data.get('classification_code') or entry.get('classification_code', '—'),
        'kemler':              _kemler_final if _kemler_final else '—',
        'tunnel_code':         _tunnel_final if _tunnel_final else '—',
        'label':               pg_data.get('label', entry.get('class', '—')),
        'packing_group':       _pg_final,
        'special_provisions':  entry.get('special_provisions', []),
        'limited_qty':         (lambda lq: lq.get(_pg_final, '—') if isinstance(lq, dict) else (lq or '—'))(entry.get('limited_qty', '—')),
        # IMDG ve IATA için sınıf aynı, isim farklı olabilir
        'imdg_class':          entry.get('class', '—'),
        'iata_class':          entry.get('class', '—'),
        'found': True,
    }


# auto_detect_un() KALDIRILDI.
# Transport sınıflandırması tek kaynaktan yapılır: js/engines/transport_engine.js
# Bu fonksiyonu çağıran herhangi bir kod varsa transport_engine.js çıktısını kullanacak şekilde güncelleyin.


if __name__ == '__main__':
    # Test
    print(get_adr_details('UN1993', 'II'))
    print()
    print(auto_detect_un(['H225', 'H315']))
