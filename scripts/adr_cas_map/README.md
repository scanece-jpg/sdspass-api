# ADR Tablo A → CAS eşlemesi (data/adr_cas_map.json)

Tablo A'da CAS numarası yoktur; tek madde adlı girişler CAS'a bu betiklerle eşlenir (2026-10-10).
Sırayla çalıştırın (ara dosyalar bu klasöre yazılır, git'e girmez):

    python scripts/adr_cas_map/1_adaylar.py     # adr_data.json → tek madde adayları (ad, hal, derişim koşulu)
    python scripts/adr_cas_map/2_pubchem.py     # PubChem ad → CAS (yavaş; 429 sınırlamasında bekler) — isteğe bağlı
    python scripts/adr_cas_map/3_birlestir.py   # Ek-6 (substance_db) + Wikidata (UN↔CAS) + PubChem; çelişenler dışarıda
    python scripts/adr_cas_map/4_harita.py      # kabul kuralları → data/adr_cas_map.json + ta_inceleme.txt

Kabul kuralları: Ek-6 tek ad eşleşmesi → kabul; PubChem birebir ad → Wikidata ile çelişmiyorsa kabul;
yalnız Wikidata → Ek-6 sınıfı uyumluysa ya da PubChem aynı CAS'ı veriyorsa kabul; Ek-6'da olup taşıma zararı
olmayan madde → ret. Elle eklenen girişler (transport_adr_service._SEED_ENTRIES) her zaman önceliklidir.
Ek adımlar: `5_tablo_b.py` (ADR Tablo B dizini × Ek-6; Tablo B ADR'nin resmî parçası değildir — yalnız doğrulama/ek) 4'ten önce;
`6_gruplar.py` → data/adr_group_map.json (ADR 2.1.3.6 kimyasal grup B.B.B.; IUPAC ad ekleri, KDU gözden geçirmeli).
ADR 2027 çıkınca: önce scripts/adr_tablea_kontrol.py, sonra bu dört adım.
