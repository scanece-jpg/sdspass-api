"""ADR 2.1.3.6 "en özel toplu giriş" için kimyasal grup üyeliği: SEA Ek-6 İngilizce adlarına IUPAC adlandırma ekleri
uygulanır (-ol alkol, -on keton, -al aldehit, -oat/asetat ester, eter/alkoksi eter, -amin amin); hidrokarbonlar yalnız
hidrokarbon adı parçalarından oluşan adlarla; kostik alkali açık listeyle. Çıktı: data/adr_group_map.json (CAS → [grup]).
Adlandırma kuralıdır, kimyasal yapı doğrulaması değildir — çıktıyı KDU gözden geçirmelidir.
Kullanım: python scripts/adr_cas_map/6_gruplar.py"""
import sys, os, re, json, io, collections
HERE = os.path.dirname(os.path.abspath(sys.argv[0]))
os.chdir(os.path.dirname(os.path.dirname(HERE))); sys.stdout.reconfigure(encoding='utf-8')
DB = json.load(open('data/substance_db.json', encoding='utf-8'))

INORG = re.compile(r'sodium|potassium|lithium|calcium|magnesium|zinc|copper|iron|alumin|ammonium|silver|\btin\b|lead|'
                   r'barium|nickel|cobalt|chrom|mangan|titan|zircon|boron|bor[ai]|silic|silan|silox|mercury|cadmium|arsen|'
                   r'selen|thall|antimon|bismuth|tungst|molybd|vanad|strontium|caesium|cesium|rubidium|beryll|'
                   r'chloro|bromo|fluoro|iodo|chloride|bromide|fluoride|iodide|nitro|nitrate|nitrite|sulf|sulph|phosph|'
                   r'acid|salt|oxide|peroxide|hydroperoxide|isocyanat|cyan|nitrile|azo|hydrazin|mixture|reaction mass|'
                   r'peroxy|polymer|ester of|esters of|compound|\bmass\b|isothiazol|thiazol|triazin|imidazol|oxazol|pyrrolidon|'
                   r'lactone|lactam|quinone|amide\b|amido|carbamate|urea|guanid')
G_RX = {
    'alkol':   re.compile(r'(anol|enol|ynol|diol|triol)\b|alcohol|glycol\b'),
    'keton':   re.compile(r'(an|en)-?\d*(,\d+)*-?(di)?one\b|\bketone\b'),
    'aldehit': re.compile(r'(an|en)al\b|aldehyde'),
    'ester':   re.compile(r'(acetate|formate|propionate|propanoate|butyrate|butanoate|acrylate|valerate|pentanoate|'
                          r'hexanoate|benzoate|lactate|oate)\b'),
    'eter':    re.compile(r'\bether\b|dioxane|tetrahydrofuran|oxolane|(meth|eth|prop|but|pent|hex)oxy'),
    'amin':    re.compile(r'amine\b|amine\)|amino|morpholine|piperazine|piperidine|pyrrolidine\b'),
}
PHENOL = re.compile(r'phenol|cresol|xylenol|naphthol|benzenediol|catechol|resorcin|hydroquinone|thymol')
HC_TOKENS = r'(cyclo|iso|neo|tert|sec|di|tri|tetra|meth|eth|prop|but|pent|hex|hept|oct|non|dec|undec|dodec|yl|ylidene|' \
            r'vinyl|allyl|phenyl|benz|ane|ene|yne|diene|toluene|xylene|cumene|styrene|naphthalene|mesitylene|benzene|' \
            r'alpha|beta|[nomp])'
HC = re.compile(r'^(' + HC_TOKENS + r')+$')
KOSTIK = {'1310-73-2', '1310-58-3', '1310-65-2', '1310-82-3', '21351-79-1'}   # Na, K, Li, Rb, Cs hidroksit
# Ek-6'da grup satırında olduğu için (tek ada eşlenemeyen) sık hidrokarbonlar: ksilen ve izomerleri
HC_EK = {'1330-20-7', '95-47-6', '108-38-3', '106-42-3'}


def groups_of(name: str) -> set:
    raw = name.lower()
    if INORG.search(raw):
        return set()
    # yalnız basit adlar (solventler vb.): ilk eş anlamlı, [n] notları dışında köşeli/normal parantez yok, ≤ 40 karakter
    syn = [re.sub(r'\[\d+\]', ' ', x).strip() for x in raw.split(';')]
    syn = [x for x in syn if x and len(x) <= 40 and not re.search(r'[\[\]()]', x)]
    if not syn or len(re.sub(r'\[\d+\]', ' ', raw.split(';')[0]).strip()) > 40:
        return set()
    out = {g for g, rx in G_RX.items() for x in syn if rx.search(x)}
    if 'alkol' in out and any(PHENOL.search(x) for x in syn):
        out.discard('alkol')
    if not out:
        for x in syn:
            flat = re.sub(r'[\d,\-\s\'′]', '', x)
            if flat and HC.match(flat):
                out.add('hidrokarbon')
    return out


res = {c: ['hidrokarbon'] for c in HC_EK}
for cas, e in DB.items():
    if cas in KOSTIK:
        res[cas] = ['kostik_alkali']; continue
    if cas in HC_EK:
        res[cas] = ['hidrokarbon']; continue
    try:
        names = eval(e.get('names') or '[]') if isinstance(e.get('names'), str) else (e.get('names') or [])
    except Exception:
        names = []
    if len(names) != 1:
        continue                      # Ek-6 grup satırı — tek maddeye ait değil
    g = groups_of(str(names[0]))
    if g:
        res[cas] = sorted(g)
out = {'kaynak': 'SEA Ek-6 İngilizce adları + IUPAC adlandırma ekleri (adlandırma kuralı); kostik alkali açık liste. '
                 'scripts/adr_cas_map/6_gruplar.py, 2026-10-10. KDU gözden geçirmeli.', 'grup': res}
io.open('data/adr_group_map.json', 'w', encoding='utf-8', newline='').write(json.dumps(out, ensure_ascii=False, indent=0))
cnt = collections.Counter(g for v in res.values() for g in v)
print(len(res), 'madde gruplandı:', dict(cnt))
