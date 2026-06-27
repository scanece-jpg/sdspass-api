"""
REACH Kayıt Numaraları ve EC No Veritabanı
Kaynak: ECHA Registered Substances (ECHA.europa.eu)
Format: CAS → {reg: [kayıt no], ec: EC no, name: İngilizce ad}
"""

REACH_DB: dict = {
    # ── Çözücüler ─────────────────────────────────────────────────────────────
    '1330-20-7': {'reg':['01-2119488216-32-0001'],'ec':'215-535-7','name':'Xylenes'},
    '67-64-1':   {'reg':['01-2119471330-49-0000'],'ec':'200-662-2','name':'Acetone'},
    '64-17-5':   {'reg':['01-2119457610-43-0000'],'ec':'200-578-6','name':'Ethanol'},
    '67-56-1':   {'reg':['01-2119433307-44-0000'],'ec':'200-659-6','name':'Methanol'},
    '71-43-2':   {'reg':['01-2119447106-44-0000'],'ec':'200-753-7','name':'Benzene'},
    '108-88-3':  {'reg':['01-2119471310-51-0000'],'ec':'203-625-9','name':'Toluene'},
    '100-41-4':  {'reg':['01-2119489084-34-0000'],'ec':'202-849-4','name':'Ethylbenzene'},
    '78-93-3':   {'reg':['01-2119457472-47-0000'],'ec':'201-159-0','name':'Methyl ethyl ketone (MEK)'},
    '141-78-6':  {'reg':['01-2119475103-46-0000'],'ec':'205-500-4','name':'Ethyl acetate'},
    '110-54-3':  {'reg':['01-2119480137-45-0000'],'ec':'203-777-6','name':'n-Hexane'},
    '142-82-5':  {'reg':['01-2119480533-43-0000'],'ec':'205-563-8','name':'Heptane'},
    '110-82-7':  {'reg':['01-2119453971-44-0000'],'ec':'203-806-2','name':'Cyclohexane'},
    '75-09-2':   {'reg':['01-2119480404-40-0000'],'ec':'200-838-9','name':'Dichloromethane'},
    '79-01-6':   {'reg':['01-2119471751-33-0000'],'ec':'201-167-4','name':'Trichloroethylene'},
    '127-18-4':  {'reg':['01-2119452073-46-0000'],'ec':'204-825-9','name':'Tetrachloroethylene'},
    '56-23-5':   {'reg':['01-2119487813-28-0000'],'ec':'200-262-8','name':'Carbon tetrachloride'},
    '67-63-0':   {'reg':['01-2119457558-25-0000'],'ec':'200-661-7','name':'Isopropanol (IPA)'},
    '71-36-3':   {'reg':['01-2119484630-38-0000'],'ec':'200-751-6','name':'n-Butanol'},
    '78-83-1':   {'reg':['01-2119484609-23-0000'],'ec':'201-148-0','name':'Isobutanol (2-methylpropan-1-ol)'},
    '123-86-4':  {'reg':['01-2119485493-29-0000'],'ec':'204-658-1','name':'n-Butyl acetate'},
    '108-94-1':  {'reg':['01-2119453655-35-0000'],'ec':'203-631-1','name':'Cyclohexanone'},
    # ── Su ve temel maddeler ──────────────────────────────────────────────────
    '7732-18-5': {'reg':['01-2119558006-37-0000'],'ec':'231-791-2','name':'Water'},
    '7647-01-0': {'reg':['01-2119484862-27-0000'],'ec':'231-595-7','name':'Hydrochloric acid'},
    '7664-93-9': {'reg':['01-2119458838-20-0000'],'ec':'231-639-5','name':'Sulfuric acid'},
    '7664-41-7': {'reg':['01-2119488166-29-0000'],'ec':'231-635-3','name':'Ammonia'},
    '7697-37-2': {'reg':['01-2119490100-40-0000'],'ec':'231-714-2','name':'Nitric acid'},
    '1310-73-2': {'reg':['01-2119457892-27-0000'],'ec':'215-185-5','name':'Sodium hydroxide'},
    '1310-58-3': {'reg':['01-2119487136-33-0000'],'ec':'215-181-3','name':'Potassium hydroxide'},
    '7778-18-9': {'reg':['01-2119444918-26-0000'],'ec':'231-900-3','name':'Calcium sulfate'},
    '497-19-8':  {'reg':['01-2119485157-39-0000'],'ec':'207-838-8','name':'Sodium carbonate'},
    '144-55-8':  {'reg':['01-2119490220-48-0000'],'ec':'205-633-8','name':'Sodium bicarbonate'},
    # ── Sanayi kimyasalları ───────────────────────────────────────────────────
    '13463-67-7':{'reg':['01-2119489379-17-0000'],'ec':'236-675-5','name':'Titanium dioxide'},
    '1344-28-1': {'reg':['01-2119529248-35-0000'],'ec':'215-691-6','name':'Aluminium oxide'},
    '14808-60-7':{'reg':['01-2119379499-16-0000'],'ec':'238-878-4','name':'Quartz (SiO2)'},
    '7440-22-4': {'reg':['01-2119480668-26-0000'],'ec':'231-131-3','name':'Silver'},
    '7440-50-8': {'reg':['01-2119480154-42-0000'],'ec':'231-159-6','name':'Copper'},
    '7440-66-6': {'reg':['01-2119467174-37-0000'],'ec':'231-175-3','name':'Zinc'},
    '7440-02-0': {'reg':['01-2119438727-29-0000'],'ec':'231-111-4','name':'Nickel'},
    '7439-97-6': {'reg':['01-2119440024-38-0000'],'ec':'231-106-7','name':'Mercury'},
    '7439-92-1': {'reg':['01-2119513221-59-0000'],'ec':'231-100-4','name':'Lead'},
    '7440-47-3': {'reg':['01-2119485652-27-0000'],'ec':'231-157-5','name':'Chromium'},
    # ── Biyositler ve pestisitler ─────────────────────────────────────────────
    '2682-20-4': {'reg':['01-2120103039-72-0000'],'ec':'220-239-6','name':'MIT (Methylisothiazolinone)'},
    '26172-55-4':{'reg':['01-2119514946-26-0000'],'ec':'247-500-7','name':'CMIT (Chloromethylisothiazolinone)'},
    '55965-84-9':{'reg':['01-2119487399-23-0000'],'ec':'611-341-5','name':'MIT/CMIT mixture (3:1)'},
    '2921-88-2': {'reg':['01-2119488576-15-0000'],'ec':'220-864-4','name':'Chlorpyrifos'},
    '94-75-7':   {'reg':['01-2119485591-18-0000'],'ec':'202-361-1','name':'2,4-D'},
    # ── Boyar maddeler ve pigmentler ─────────────────────────────────────────
    '13463-67-7':{'reg':['01-2119489379-17-0000'],'ec':'236-675-5','name':'Titanium dioxide (white pigment)'},
    # ── Yüzey aktif maddeler ──────────────────────────────────────────────────
    '151-21-3':  {'reg':['01-2119489428-22-0000'],'ec':'205-788-1','name':'Sodium lauryl sulfate (SLS)'},
    '9016-45-9': {'reg':['exempt'],'ec':'500-315-8','name':'Nonylphenol ethoxylate (NPE)'},
    # ── Monomerler/polimerler ─────────────────────────────────────────────────
    '75-21-8':   {'reg':['01-2119475670-40-0000'],'ec':'200-849-9','name':'Ethylene oxide'},
    '100-42-5':  {'reg':['01-2119457861-32-0000'],'ec':'202-851-5','name':'Styrene'},
    '9003-22-9': {'reg':['polymer'],'ec':'—','name':'Vinyl chloride-vinyl acetate copolymer'},
    # ── Yapı kimyasalları ─────────────────────────────────────────────────────
    '1305-62-0': {'reg':['01-2119471028-30-0000'],'ec':'215-137-3','name':'Calcium hydroxide'},
    '1305-78-8': {'reg':['01-2119475635-27-0000'],'ec':'215-138-9','name':'Calcium oxide'},
    '7631-86-9': {'reg':['01-2119444456-42-0000'],'ec':'231-545-4','name':'Amorphous silica'},

    # ── Su arıtma inhibitörleri ────────────────────────────────────────────────
    '37971-36-1': {'reg':['01-2119510325-52-0000'],'ec':'253-733-5','name':'PBTC (2-Phosphono-1,2,4-butanetricarboxylic acid)'},
    '2809-21-4':  {'reg':['01-2119486946-17-0000'],'ec':'220-552-8','name':'HEDP (1-Hydroxyethane-1,1-diphosphonic acid)'},
    '6419-19-8':  {'reg':['01-2119518542-42-0000'],'ec':'229-146-5','name':'ATMP (Nitrilotris(methylenephosphonic acid))'},
    '15827-60-8': {'reg':['01-2119520432-46-0000'],'ec':'239-931-4','name':'DTPMPA'},
    '9003-01-4':  {'reg':['polymer'],'ec':'618-339-5','name':'Polyacrylic acid (PAA)'},
    '527-07-1':   {'reg':['01-2119488568-23-0000'],'ec':'208-407-7','name':'Sodium gluconate'},
    '102-71-6':   {'reg':['01-2119475503-37-0000'],'ec':'203-049-8','name':'Triethanolamine (TEA)'},
    '57-55-6':    {'reg':['01-2119456809-23-0000'],'ec':'200-338-0','name':'Propylene glycol'},
    '107-21-1':   {'reg':['01-2119456816-28-0000'],'ec':'203-473-3','name':'Ethylene glycol'},
    '7631-95-0':  {'reg':['01-2119529016-51-0000'],'ec':'231-551-7','name':'Sodium molybdate'},
    '7733-02-0':  {'reg':['01-2119513990-41-0000'],'ec':'231-793-3','name':'Zinc sulfate'},
    '111-30-8':   {'reg':['01-2119813636-29-0000'],'ec':'203-856-5','name':'Glutaraldehyde'},
    '10222-01-2': {'reg':['01-2119980150-41-0000'],'ec':'233-539-7','name':'DBNPA'},
    '55566-30-8': {'reg':['01-2119980248-28-0000'],'ec':'259-709-0','name':'THPS'},
    '7681-52-9':  {'reg':['exempt'],'ec':'231-668-3','name':'Sodium hypochlorite'},
    '77-92-9':    {'reg':['01-2119457026-42-0000'],'ec':'201-069-1','name':'Citric acid'},
    '7664-38-2':  {'reg':['01-2119485924-24-0000'],'ec':'231-633-2','name':'Phosphoric acid'},
    '7758-29-4':  {'reg':['01-2119489488-18-0000'],'ec':'231-838-7','name':'Sodium tripolyphosphate (STPP)'},
    '40623-75-4': {'reg':['01-2119943620-36-0000'],'ec':'255-124-2','name':'AMPS (2-Acrylamido-2-methylpropanesulfonic acid)'},
    '29385-43-1': {'reg':['01-2119978103-39-0000'],'ec':'249-596-6','name':'Tolyltriazole (TTA)'},
    '95-14-7':    {'reg':['01-2119978648-16-0000'],'ec':'202-394-1','name':'Benzotriazole (BTA)'},

    # ── Fosfonat tuzları (su arıtma) ──────────────────────────────────────────
    '7414-83-7':  {'reg':['01-2119486971-25-0000'],'ec':'231-082-4','name':'HEDP.Na (Sodium etidronate)'},
    '25384-17-2': {'reg':['01-2119486971-25-0000'],'ec':'246-978-0','name':'HEDP.Na2 (Disodium etidronate)'},
    '3794-83-0':  {'reg':['01-2119486971-25-0000'],'ec':'223-267-7','name':'HEDP.Na4 (Tetrasodium etidronate)'},
    '20592-85-2': {'reg':['01-2119518542-42-0000'],'ec':'243-960-0','name':'ATMP.Na5 (Pentasodium ATMP)'},
    '40372-66-5': {'reg':['01-2119510325-52-0000'],'ec':'254-898-0','name':'PBTC.Na (Sodium PBTC)'},
    '22042-96-2': {'reg':['01-2119520432-46-0000'],'ec':'244-759-8','name':'DTPMPA.Na5'},
    '1429-50-1':  {'reg':['01-2119976027-28-0000'],'ec':'215-851-3','name':'EDTMPA'},
    '51274-37-4': {'reg':['polymer'],'ec':'257-098-5','name':'PESA (Polyepoxysuccinic acid Na)'},
    '23783-26-8': {'reg':['01-2119973903-31-0000'],'ec':'245-910-6','name':'HPAA (Hydroxyphosphonoacetic acid)'},
    '70715-06-9': {'reg':['01-2119973903-31-0001'],'ec':'274-877-8','name':'HPCA (2-Hydroxyphosphonocarboxylic acid)'},
    # ── İnorganik tuzlar ─────────────────────────────────────────────────────
    '7786-30-3':  {'reg':['01-2119485597-19-0000'],'ec':'232-094-6','name':'Magnesium chloride'},
}


def get_reach(cas: str) -> dict | None:
    """CAS numarasından REACH bilgilerini getir."""
    return REACH_DB.get(cas.strip())


def get_reg_no(cas: str) -> str:
    """İlk kayıt numarasını döndür: statik DB → disk önbelleği → boş string."""
    cas = cas.strip()
    d = REACH_DB.get(cas)
    if d:
        regs = d.get('reg', [])
        if regs and regs[0] not in ('exempt', 'polymer'):
            return regs[0]
        return regs[0] if regs else ''
    # Statik DB'de yoksa disk önbelleğini dene
    try:
        from app.services.reach_cache import load_cached
        cached = load_cached(cas)
        if cached:
            return cached
    except Exception:
        pass
    return ''


def get_ec_no(cas: str) -> str:
    """EC numarasını döndür."""
    d = REACH_DB.get(cas.strip())
    return d.get('ec', '') if d else ''


if __name__ == '__main__':
    print(f"REACH DB: {len(REACH_DB)} madde")
    for cas in ['1330-20-7', '7732-18-5', '2682-20-4']:
        print(f"  {cas}: EC={get_ec_no(cas)}, Reg={get_reg_no(cas)}")
