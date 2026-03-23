#!/bin/bash
# SDSPass — Nginx + SSL Kurulum
# root olarak çalıştır
set -e

echo "=== Nginx + SSL Kurulum ==="

# ── Nginx config ─────────────────────────────────────────────────────────────

# api.sdspass.com — FastAPI backend
cat > /etc/nginx/sites-available/api.sdspass.com << 'NGINX'
server {
    listen 80;
    server_name api.sdspass.com;

    # Security headers (ISO 27001 uyumlu)
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate limiting (DDoS koruması)
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;

        # CORS — app.sdspass.com ve sdspass.com.tr'den izin ver
        add_header Access-Control-Allow-Origin "https://app.sdspass.com" always;
        add_header Access-Control-Allow-Origin "https://sdspass.com.tr" always;
        add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization" always;
    }

    # PDF endpoint için daha büyük body (büyük formüller)
    location /api/v1/sds/pdf {
        proxy_pass http://127.0.0.1:8000;
        client_max_body_size 5M;
        proxy_read_timeout 120s;
    }
}
NGINX

# app.sdspass.com — Hesaplama arayüzü (static HTML)
cat > /etc/nginx/sites-available/app.sdspass.com << 'NGINX'
server {
    listen 80;
    server_name app.sdspass.com;

    root /var/www/sdspass;
    index index.html;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header Content-Security-Policy "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://api.sdspass.com" always;

    location / {
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, must-revalidate";
    }

    # HTML dosyasını cache'leme (güncel kalması için)
    location ~* \.html$ {
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }
}
NGINX

# sdspass.com ve sdspass.com.tr — Landing page
cat > /etc/nginx/sites-available/sdspass.com << 'NGINX'
server {
    listen 80;
    server_name sdspass.com www.sdspass.com sdspass.com.tr www.sdspass.com.tr;

    root /var/www/sdspass/landing;
    index index.html;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # /app → app.sdspass.com'a yönlendir
    location /app {
        return 301 https://app.sdspass.com;
    }
}
NGINX

# Sites enable
ln -sf /etc/nginx/sites-available/api.sdspass.com /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/app.sdspass.com /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/sdspass.com    /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t && systemctl reload nginx
echo "✓ Nginx konfigürasyonu aktif"

# ── SSL Sertifikaları ─────────────────────────────────────────────────────────
echo ""
echo "SSL sertifikaları alınıyor..."
echo "NOT: DNS kayıtları sunucuya yönlendirilmiş olmalı!"
echo ""

certbot --nginx \
    -d sdspass.com -d www.sdspass.com \
    -d sdspass.com.tr -d www.sdspass.com.tr \
    -d api.sdspass.com \
    -d app.sdspass.com \
    --non-interactive --agree-tos \
    --email admin@sdspass.com \
    --redirect

echo "✓ SSL sertifikaları kuruldu"

# Otomatik yenileme
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet") | crontab -
echo "✓ SSL otomatik yenileme ayarlandı"

echo ""
echo "=== Nginx + SSL Kurulum Tamamlandı ==="
echo ""
echo "Kontrol et:"
echo "  curl https://api.sdspass.com/health"
echo "  curl https://app.sdspass.com"
