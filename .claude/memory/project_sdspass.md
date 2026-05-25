---
name: project_sdspass
description: GBF/SDS hazırlama sistemi — KKDİK/CLP uyumlu güvenlik bilgi formu otomatik üretici
type: project
---

# SDSPass Projesi

Kimyasal ürünler için KKDİK (Türkiye) ve CLP (AB) yönetmeliklerine uygun Güvenlik Bilgi Formu (GBF/SDS) otomatik hazırlayan sistem.

## Proje Dizinleri
- Çalışma kopyası: `C:\Users\user\Desktop\sdspass\`
- GitHub: scanece-jpg/sdspass-api
- Canlı adres: https://sdspass-api-3.onrender.com/
- Render.com **manuel deploy** — git push sonrası Render panelinden "Deploy" butonuna basılmalı

## Mimari
- Frontend: `static/index.html` + `js/engines/*.js` (8 motor, tarayıcıda hesaplama)
- Backend: FastAPI (`app/main.py`) + ReportLab PDF (`app/services/pdf_sds_service.py`)
- Veri: `data/clp_full_data.json`, `data/adr_data.json`

## Önemli Kısıtlamalar
- Font: Türkçe karakterler için render.yaml'da `apt-get install fonts-dejavu-core` gerekli
- JS cache: `index.html`'deki `?v=YYYYMMDD` versiyonunu güncellemek gerekir
- Deploy: değişiklik → `C:\Users\user\Desktop\sdspass\` → git add/commit/push → Render otomatik deploy

## İki Kopya Uyarısı
`hazarddesk_deploy` (çalışma kopyası) ve `sdspass` (git kopyası) — değişiklik sonrası ikisi senkron olmalı.

**Why:** Sistem KKDİK, CLP, SEA, ADR, IMDG, IATA, REACH, GHS yönetmeliklerine uygun 16 bölümlü PDF üretir.
**How to apply:** Değişiklik önerirken her zaman yönetmelik uyumluluğunu göz önünde bulundur. Deploy için sdspass dizinini kullan.
