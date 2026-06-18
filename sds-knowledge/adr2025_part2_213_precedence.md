# ADR 2025 — §2.1.3.10: Tehlike Öncelik Tablosu (Table of Precedence of Hazards)

> Kaynak: ADR 2025 Vol.I (ECE/TRANS/352), Chapter 2.1, §2.1.3.10, PDF sayfa 127–128
> 1 Ocak 2025 tarihinden itibaren geçerlidir.

---

## §2.1.3.5.3 — Birincil Tehlike Sırası (Mutlak Öncelik)

Aşağıdaki sınıflar için §2.1.3.10 tablosuna gerek yoktur; sıralama doğrudan uygulanır:

1. Sınıf 7 materyaller (a)
2. Sınıf 1 maddeleri (b)
3. Sınıf 2 maddeleri (c)
4. Sınıf 3 sıvı duyarsızlaştırılmış patlayıcılar (d)
5. Sınıf 4.1 kendiliğinden tepkimeye giren maddeler ve katı duyarsızlaştırılmış patlayıcılar (e)
6. Sınıf 4.2 piroforik maddeler (f)
7. Sınıf 5.2 organik peroksitler (g)
8. Sınıf 6.1 inhalasyon toksisitesi PG I (h)
9. Sınıf 6.2 enfeksiyöz maddeler (i)

## §2.1.3.5.4 — §2.1.3.10 Tablosunun Kullanım Koşulu

Yukarıdaki listede **yer almayan** sınıf kombinasyonlarında (örneğin Sınıf 3 + Sınıf 8, Sınıf 5.1 + Sınıf 8) birincil tehlike **§2.1.3.10 tablosuna göre** belirlenir.

---

## §2.1.3.10 — Tehlike Öncelik Matrisi

Tabloda **satır** = birinci tehlike sınıfı/PG, **sütun** = ikinci tehlike sınıfı/PG.
Hücredeki değer = iki tehlike arasında **birincil sınıflandırma olarak seçilecek** sınıf/PG'dir.

> **LIQ** = sıvı/çözelti (Liquid), **SOL** = katı (Solid) için farklı sonuç.
> ᵃ = sınıf 6.1 için pestisit istisnası.

| Satır \\ Sütun | 3-I | 3-II | 3-III | 4.1-II | 4.1-III | 4.2-II | 4.2-III | 4.3-I | 4.3-II | 4.3-III | 5.1-I | 5.1-II | 5.1-III | 6.1-I(derm) | 6.1-I(oral) | 6.1-II(inh) | 6.1-II(derm) | 6.1-II(oral) | 6.1-III | 8-I | 8-II | 8-III |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **4.1-II** | LIQ:3-I SOL:1.4-II | LIQ:3-II SOL:1.4-II | LIQ:3-II SOL:1.4-II | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **4.1-III** | LIQ:3-I SOL:1.4-III | LIQ:3-II SOL:1.4-III | LIQ:3-III SOL:1.4-III | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **4.2-II** | LIQ:3-I SOL:2.4 | LIQ:3-II SOL:2.4 | LIQ:3-II SOL:2.4 | 4.2-II | 4.2-II | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **4.2-III** | LIQ:3-I SOL:2.4 | LIQ:3-II SOL:2.4 | LIQ:3-III SOL:2.4 | 4.2-II | 4.2-III | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **4.3-I** | 4.3-I | 4.3-I | 4.3-I | 4.3-I | 4.3-I | 4.3-I | 4.3-I | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **4.3-II** | 4.3-I | 4.3-II | 4.3-II | 4.3-II | 4.3-II | 4.3-II | 4.3-II | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **4.3-III** | 4.3-I | 4.3-II | 4.3-III | 4.3-II | 4.3-III | 4.3-II | 4.3-III | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| **5.1-I** | LIQ:3-I SOL:5.1-I | LIQ:3-I SOL:5.1-I | LIQ:3-I SOL:5.1-I | 5.1-I | 5.1-I | 5.1-I | 5.1-I | 5.1-I | 5.1-I | 5.1-I | — | — | — | — | — | — | — | — | — | — | — | — |
| **5.1-II** | LIQ:3-I SOL:5.1-II | LIQ:3-II SOL:5.1-II | LIQ:3-II SOL:5.1-II | 4.1-II | 4.1-II | 4.2-II | 5.1-II | 4.3-I | 4.3-II | 5.1-II | — | — | — | — | — | — | — | — | — | — | — | — |
| **5.1-III** | LIQ:3-I SOL:5.1-III | LIQ:3-II SOL:5.1-III | LIQ:3-III SOL:5.1-III | 4.1-II | 4.1-III | 4.2-II | 4.2-III | 4.3-I | 4.3-II | 4.3-III | — | — | — | — | — | — | — | — | — | — | — | — |
| **6.1-I(oral)** | 3-I | 3-I | 6.1-I | 6.1-I | 6.1-I | 6.1-I | 6.1-I | 4.3-I | 4.3-I | 6.1-I | 5.1-I | 5.1-I | 6.1-I | — | — | — | — | — | — | — | — | — |
| **6.1-I(derm)** | 3-I | 3-I | 6.1-I | 6.1-I | 6.1-I | 6.1-I | 6.1-I | 6.1-I | 6.1-I | 6.1-I | 5.1-I | 6.1-I | 6.1-I | — | — | — | — | — | — | — | — | — |
| **6.1-II(oral)** | 3-I | 3-II | ᵃ3-III | LIQ:6.1-II SOL:1.4-II | 6.1-II | 4.2-II | 6.1-II | 4.3-I | 4.3-II | 6.1-II | 5.1-I | 5.1-II | 6.1-II | — | — | — | — | — | — | — | — | — |
| **6.1-II(derm)** | 3-I | 3-II | 6.1-II | LIQ:6.1-II SOL:1.4-II | LIQ:6.1-III SOL:1.4-III | 4.2-II | 6.1-II | 4.3-I | 4.3-II | 6.1-II | 5.1-I | 5.1-II | 6.1-II | — | — | — | — | — | — | — | — | — |
| **6.1-III** | 3-I | 3-II | 3-III | 4.1-II | 4.1-III | 4.2-II | 4.2-III | 4.3-I | 4.3-II | 4.3-III | 5.1-I | 5.1-II | 5.1-III | — | — | — | — | — | — | — | — | — |
| **8-I** | 3-I | 8-I | 8-I | 8-I | 8-I | 8-I | 8-I | 4.3-I | 8-I | 8-I | 5.1-I | 8-I | 8-I | LIQ:8-I SOL:6.1-I | LIQ:8-I SOL:6.1-I | LIQ:8-I SOL:6.1-I | LIQ:8-I SOL:6.1-I | 8-I | 8-I | — | — | — |
| **8-II** | 3-I | 3-II | 8-II | LIQ:8-II SOL:1.4-II | 8-II | 4.2-II | 8-II | 4.3-I | 4.3-II | 8-II | 5.1-I | 5.1-II | 8-II | 6.1-I | 6.1-I | 6.1-II | LIQ:8-II SOL:6.1-II | LIQ:8-II SOL:6.1-II | 8-II | — | — | — |
| **8-III** | 3-I | 3-II | 3-III | LIQ:8-III SOL:1.4-III | 8-III | 4.2-II | 4.2-III | 4.3-I | 4.3-II | 4.3-III | 5.1-I | 5.1-II | 5.1-III | 6.1-I | 6.1-I | 6.1-II | 6.1-II | 6.1-II | 8-III | — | — | — |

---

## Örnekler (§2.1.3.10, Sayfa 128)

### Tek Madde
Madde: Sınıf 3 PG II + Sınıf 8 PG I özelliklerini taşıyan bir amin.
- Tablo: satır 3-II ∩ sütun 8-I → **8-I**
- Sonuç: **UN 2734 AMINES LIQUID, CORROSIVE, FLAMMABLE, N.O.S., Sınıf 8, PG I**

### Karışım
Bileşenler: Sınıf 3 PG III + Sınıf 6.1 PG II + Sınıf 8 PG I içeren karışım.
- Adım 1: satır 3-III ∩ sütun 6.1-II → 6.1-II
- Adım 2: satır 6.1-II ∩ sütun 8-I → **8-I (LIQ)**
- Sonuç: **UN 2922 CORROSIVE LIQUID, TOXIC, N.O.S., Sınıf 8, PG I**

---

## BULGU 5 Referansı: UN 3098 vs UN 3093

| UN | Proper Shipping Name | Sınıf | PG | Açıklama |
|----|---------------------|-------|----|----------|
| UN3093 | CORROSIVE LIQUID, OXIDIZING, N.O.S. | 8 | I | Birincil tehlike: aşındırıcı |
| UN3098 | OXIDIZING LIQUID, CORROSIVE, N.O.S. | 5.1 | II/III | Birincil tehlike: yükseltgen |

**Tablo kararı:**
- 5.1-I + 8-I → **5.1-I** (beşinci satır: 5.1-I kazanır)
- 5.1-II + 8-I → **8-I** (sekizinci satır)
- 5.1-III + 8-I → **8-I** (dokuzuncu satır)

Yani:
- PG I yükseltgen + PG I aşındırıcı → **5.1-I öncelikli** → UN3097
- PG II/III yükseltgen + PG I aşındırıcı → **8-I öncelikli** → UN3093
- PG II/III yükseltgen + PG II/III aşındırıcı → **5.1 öncelikli** → UN3098/UN3099
