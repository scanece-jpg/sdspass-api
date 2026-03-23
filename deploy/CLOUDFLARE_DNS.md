# SDSPass — Cloudflare DNS Ayarları

## 1. Cloudflare'e ekle
- cloudflare.com → Add Site → sdspass.com
- Plan: Free
- Nameserver'ları domain kayıt firmasına gir

## 2. DNS Kayıtları (sdspass.com)

| Type  | Name        | Content         | Proxy  |
|-------|-------------|-----------------|--------|
| A     | @           | SUNUCU_IP       | ✓ ON   |
| A     | www         | SUNUCU_IP       | ✓ ON   |
| A     | app         | SUNUCU_IP       | ✓ ON   |
| A     | api         | SUNUCU_IP       | ✓ ON   |
| CNAME | mail        | mail.sdspass.com| ✗ OFF  |

## 3. DNS Kayıtları (sdspass.com.tr)
Aynı A kayıtlarını sdspass.com.tr için de ekle.

## 4. Cloudflare SSL Ayarları
- SSL/TLS → Full (strict)
- Always Use HTTPS → ON
- HSTS → Enable (max-age: 6 months)

## 5. Güvenlik (ISO 27001 uyumlu)
- Security → WAF → ON (free tier)
- Bot Fight Mode → ON
- Browser Integrity Check → ON
- DDoS Protection → Automatic

## NOT
SUNUCU_IP = Hetzner'den aldığın IPv4 adresi
