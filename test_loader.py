import sys
sys.path.insert(0, r'C:\Users\user\Desktop\sdspass\scripts')
from echa_excel_loader import load

rows = load(r'C:\Users\user\Desktop\sdspass\annex_vi_clp_table_atp22_en.xlsx')

for cas_test in ['7632-00-0', '10028-18-9', '13840-56-7']:
    found = False
    for r in rows:
        if cas_test in r.get('cas_list', []):
            print(cas_test, '->')
            print('  class_h_pairs:', r.get('class_h_pairs'))
            print('  cas_list:', r.get('cas_list'))
            found = True
            break
    if not found:
        print(cas_test, '-> BULUNAMADI')