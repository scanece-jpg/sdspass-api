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

    # UN no formatını normalize et
    un_key = un_no.upper().strip()
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

    # PG bulunamazsa ilk olanı al
    if not pg_data and entry.get('packing_groups'):
        pg_data = list(entry['packing_groups'].values())[0]

    return {
        'un_no':               un_key,
        'name':                entry.get('name', ''),
        'name_tr':             entry.get('name_tr', ''),
        'class':               entry.get('class', '—'),
        'classification_code': pg_data.get('classification_code') or entry.get('classification_code', '—'),
        'kemler':              pg_data.get('kemler', '—'),
        'tunnel_code':         pg_data.get('tunnel', '—'),
        'label':               pg_data.get('label', entry.get('class', '—')),
        'packing_group':       pg,
        'special_provisions':  entry.get('special_provisions', []),
        'limited_qty':         entry.get('limited_qty', {}).get(pg, '—'),
        # IMDG ve IATA için sınıf aynı, isim farklı olabilir
        'imdg_class':          entry.get('class', '—'),
        'iata_class':          entry.get('class', '—'),
        'found': True,
    }


def auto_detect_un(h_codes: list, form: str = 'liquid') -> dict | None:
    """
    H kodlarından UN numarası otomatik tespit et.
    Dönen dict doğrudan get_adr_details'e geçilebilir.
    """
    mapping = [
        (['H224'],                    'UN1224', 'I'),
        (['H225'],                    'UN1993', 'II'),
        (['H226'],                    'UN1993', 'III'),
        (['H228'],                    'UN1325', 'II'),
        (['H300', 'H310', 'H330'],    'UN2810', 'I'),
        (['H301', 'H311', 'H331'],    'UN2810', 'II'),
        (['H302', 'H312', 'H332'],    'UN2810', 'III'),
        (['H400', 'H410'],            'UN3082' if form=='liquid' else 'UN3077', 'III'),
        (['H314'],                    'UN1760', 'II'),
        (['H272'],                    'UN3139', 'III'),
        (['H271'],                    'UN3139', 'I'),
    ]

    for trigger_codes, un_no, pg in mapping:
        if any(h in h_codes for h in trigger_codes):
            details = get_adr_details(un_no, pg)
            details['auto_detected'] = True
            return details

    return None


if __name__ == '__main__':
    # Test
    print(get_adr_details('UN1993', 'II'))
    print()
    print(auto_detect_un(['H225', 'H315']))
