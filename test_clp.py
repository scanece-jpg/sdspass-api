#!/usr/bin/env python3
"""
Basit CLP Hesaplama Testi
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Test Verisi
test_components = [
    {
        "cas_no": "71-43-2",
        "name": "Benzene",
        "concentration": 50,
        "hazards": [
            {"h_class": "Flam. Liq. 2", "h_code": "H225"},
            {"h_class": "Carc. 1B", "h_code": "H350"},
            {"h_class": "Asp. Tox. 1", "h_code": "H304"}
        ]
    },
    {
        "cas_no": "67-64-1",
        "name": "Acetone",
        "concentration": 30,
        "hazards": [
            {"h_class": "Flam. Liq. 2", "h_code": "H225"},
            {"h_class": "Eye Irrit. 2", "h_code": "H319"}
        ]
    },
    {
        "cas_no": "7732-18-5",
        "name": "Water",
        "concentration": 20,
        "hazards": []
    }
]

print("=" * 80)
print("CLP HESAPLAMA MOTORU TEST")
print("=" * 80)
print()

try:
    from app.services.clp_service import classify_mixture_clp
    
    print("✅ clp_service yüklendi\n")
    
    print("📋 TEST VERİSİ:")
    print(f"   Bileşen sayısı: {len(test_components)}")
    for comp in test_components:
        print(f"   - {comp['name']} ({comp['cas_no']}) {comp['concentration']}%")
    print()
    
    print("🔄 Hesaplama yapılıyor...\n")
    result = classify_mixture_clp(test_components)
    
    print("✅ SONUÇ:")
    print(f"   H Kodları: {result['h_codes']}")
    print(f"   Sinyal Kelimesi: {result['signal_word']} ({result['signal_word_tr']})")
    print(f"   Geçen Tehlikeler: {len(result['passed'])} madde")
    
    if result['passed']:
        print("\n   Detaylar:")
        for item in result['passed']:
            print(f"      - {item['h_code']} ({item['h_class']}) → {item['reason']}")
    
    if result['warnings']:
        print(f"\n   ⚠️  Uyarılar ({len(result['warnings'])}):")
        for warn in result['warnings']:
            print(f"      - {warn}")
    
    print()
    print("=" * 80)
    print("✅ TEST BAŞARILI - Sistem çalışıyor")
    print("=" * 80)
    
except Exception as e:
    print(f"❌ HATA: {e}")
    import traceback
    traceback.print_exc()
