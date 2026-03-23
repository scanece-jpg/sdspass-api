"""
Türkiye OEL (Mesleki Maruziyet Limitleri) Servisi
===================================================
ÇSGB Yönetmeliği Ek-1 ve Kanserojen/Mutajen Maddeler
Yönetmeliği kapsamında Türkiye'ye özgü limit değerleri.
"""

import json
from pathlib import Path

_OEL_DATA = None

def _load():
    global _OEL_DATA
    if _OEL_DATA is None:
        p = Path(__file__).parent.parent.parent / 'data' / 'tr_oel_limits.json'
        if p.exists():
            with open(p) as f:
                _OEL_DATA = json.load(f)
        else:
            _OEL_DATA = {}
    return _OEL_DATA


def get_oel(cas: str) -> dict | None:
    """CAS numarasından TR OEL limitini getir."""
    return _load().get(cas.strip())


def get_oel_table(components: list) -> list:
    """
    Bileşen listesinden OEL tablosu oluştur (SDS Bölüm 8.1 için).
    
    Returns: [
        {cas, name_tr, tw_ppm, tw_mgm3, stel_ppm, stel_mgm3,
         skin, carcinogen, regulation}
    ]
    """
    rows = []
    for comp in components:
        cas = comp.get('cas_no', comp.get('cas', ''))
        oel = get_oel(cas)
        if oel:
            rows.append({
                'cas':        cas,
                'name':       comp.get('name', ''),
                'name_tr':    oel.get('name_tr', comp.get('name','')),
                'tw_ppm':     oel.get('tw_ppm'),
                'tw_mgm3':    oel.get('tw_mgm3'),
                'stel_ppm':   oel.get('stel_ppm'),
                'stel_mgm3':  oel.get('stel_mgm3'),
                'skin':       oel.get('skin', False),
                'carcinogen': oel.get('carcinogen', False),
                'regulation': oel.get('regulation', 'EK-1'),
                'notes':      oel.get('notes', ''),
            })
    return rows


def format_oel_row(row: dict, lang: str = 'TR') -> list:
    """OEL satırını PDF tablosu için formatla."""
    def fmt(ppm, mgm3):
        parts = []
        if ppm:   parts.append(f"{ppm} ppm")
        if mgm3:  parts.append(f"{mgm3} mg/m³")
        return ' / '.join(parts) if parts else '—'

    tw   = fmt(row.get('tw_ppm'),   row.get('tw_mgm3'))
    stel = fmt(row.get('stel_ppm'), row.get('stel_mgm3'))

    flags = []
    if row.get('skin'):       flags.append('Deri' if lang=='TR' else 'Skin')
    if row.get('carcinogen'): flags.append('Kans.' if lang=='TR' else 'Carc.')

    return [
        row.get('cas', ''),
        row.get('name_tr') or row.get('name', ''),
        tw,
        stel,
        ', '.join(flags) or '—',
    ]


if __name__ == '__main__':
    comps = [
        {'cas_no': '1330-20-7', 'name': 'Xylene'},
        {'cas_no': '71-43-2',   'name': 'Benzene'},
        {'cas_no': '67-64-1',   'name': 'Acetone'},
    ]
    for row in get_oel_table(comps):
        print(format_oel_row(row))
