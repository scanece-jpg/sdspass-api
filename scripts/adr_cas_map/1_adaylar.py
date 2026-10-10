"""Tablo A → tek madde adlı girişler: temel ad, hal, derişim koşulu ayrıştırma. Çıktı: ta_cand.json"""
import sys, os, re, json
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(r'C:\Users\DİPOL KİMYA\cl\sdspass-api'); sys.stdout.reconfigure(encoding='utf-8')
A = json.load(open('data/adr_data.json', encoding='utf-8'))
SKIP = re.compile(r'N\.O\.S|\bMIXTURE|\bARTICLES?\b|\bDEVICES?\b|\bKIT\b|\bWASTE\b|RADIOACTIVE|INFECTIOUS|'
                  r'\bAPPARATUS\b|\bMACHINE|\bENGINE|\bVEHICLE|\bBATTER|\bCELLS?\b|\bCARTRIDGE|\bCONTAINING\b|'
                  r'\bPREPARATIONS?\b|\bPRODUCTS?\b|\bCOMPOUNDS?\b|\bPESTICIDE|\bDYE\b|\bINK\b|\bPAINT|\bFUEL\b|'
                  r'\bEXTRACTS?\b|\bRESIN|\bADHESIVE|\bFIBRES?\b|\bFABRICS?\b|\bSAMPLE|\bDANGEROUS GOODS|'
                  r'\bFERTILIZER|\bREFRIGERANT GAS\b|\bALLOY|\bAMALGAM|\bPOLYMERIC BEADS|\bKEROSENE|\bDIESEL|\bPETROL|\bGAS OIL|'
                  r'\bTARS?\b|\bCOAL\b|\bWOOD\b|\bSEED|\bCOTTON|\bHAY\b|\bFISH|\bCOPRA|\bWOOL|\bAIRBAG|\bLIGHTER|\bMATCHES|'
                  r'\bFIREWORKS|\bFLARES|\bSIGNALS|\bAEROSOLS?\b|\bRECEPTACLES|\bINORGANIC\b|\bORGANIC\b|\bSALTS?\b|'
                  r'\bCHLORATES\b|\bPERCHLORATES\b|\bNITRATES\b|\bNITRITES\b|\bBROMATES\b|\bPERMANGANATES\b|\bPERSULPHATES\b|'
                  r'\bARSENATES?\b|\bCYANIDES\b|\bHYDRIDES\b|\bMETAL\b|\bALKALI\b|\bALKALINE\b|\bALCOHOLATES\b|\bAMINES\b|'
                  r'\bPOLYAMINES\b|\bALDEHYDES\b|\bKETONES\b|\bESTERS\b|\bETHERS\b|\bTERPENE|\bHYDROCARBONS?\b|\bISOMERS\b|'
                  r'\bCHLOROSILANES\b|\bMERCAPTANS?\b|\bPHENOLATES\b|\bMOLTEN\b|\bREFRIGERATED\b|\bWETTED\b|\bDESENSITIZED\b',
                  re.I)
STATE = [(re.compile(r'\bSOLUTION\b', re.I), 'liquid'), (re.compile(r'\bSOLID\b|\bANHYDROUS\b|\bDRY\b|\bPOWDER', re.I), 'solid'),
         (re.compile(r'\bLIQUID\b', re.I), 'liquid'), (re.compile(r'\bCOMPRESSED\b|\bLIQUEFIED\b', re.I), 'gas')]
PCT = re.compile(r'%')
out = []
for un, e in A.items():
    cls = str(e.get('class') or '')
    if cls in ('1', '7', '6.2', '—', ''):
        continue
    name = e.get('name', '')
    if SKIP.search(name):
        continue
    base = re.split(r',\s| with | containing | in solution', name, 1)[0]   # '1,1-DİKLORO…' konum virgülü bölünmez
    base = re.sub(r'\b(SOLUTION|AQUEOUS|SOLID|LIQUID|ANHYDROUS|STABILIZED|INHIBITED|DRY|HYDRATED|GLACIAL|FUMING|'
                  r'COMPRESSED|LIQUEFIED|PURE|TECHNICAL)\b', ' ', base, flags=re.I)
    base = re.sub(r'\s*[-–]\s+|\s+[-–]\s*', '-', base)          # PDF satır bölünmesi: "AMINO- ETHANOL"
    base = re.sub(r'\s*\([^)]*$', '', base)                                  # kesik parantez: "AMINOPHENOLS (o"
    full = re.sub(r'\s+', ' ', base).strip(' -,')
    base = re.sub(r'\s+', ' ', re.sub(r'\(.*?\)', ' ', base)).strip(' -,')
    if len(base) < 3 or ' or ' in base.lower() or ' and ' in base.lower():
        continue
    state = next((s for rx, s in STATE if rx.search(name)), None)
    if cls == '2':
        state = 'gas'
    pgs = sorted((e.get('packing_groups') or {}).keys()) or ([e['packing_group']] if e.get('packing_group') else [])
    out.append({'un': un, 'cls': cls, 'name': name, 'base': base, 'full': full, 'state': state, 'pgs': pgs,
                'kosul': bool(PCT.search(name))})
json.dump(out, open(os.path.join(HERE, 'ta_cand.json'), 'w', encoding='utf-8'),
          ensure_ascii=False, indent=0)
print(len(A), 'Tablo A girişi →', len(out), 'tek madde adayı;', sum(x['kosul'] for x in out), 'tanesi derişim koşullu;',
      len({x['base'].upper() for x in out}), 'farklı temel ad')
for x in out[:8]:
    print(' ', x['un'], x['cls'], x['state'], '|', x['base'], '|', x['name'][:60])
