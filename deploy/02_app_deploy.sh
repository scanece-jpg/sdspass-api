#!/bin/bash
# HazardDesk — Uygulama Deploy
# Ubuntu 24.04 | hazarddesk kullanıcısı olarak çalıştır
set -e

DOMAIN="sdspass.com"
DOMAIN_TR="sdspass.com.tr"
API_DOMAIN="api.sdspass.com"
APP_DOMAIN="app.sdspass.com"
APP_DIR="/home/hazarddesk/app"
VENV_DIR="/home/hazarddesk/venv"

echo "=== SDSPass Uygulama Deploy ==="

# 1. Uygulama dizini
mkdir -p $APP_DIR
cd $APP_DIR

# 2. Python sanal ortam
python3.12 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# 3. Bağımlılıklar
pip install --upgrade pip
pip install fastapi uvicorn[standard] httpx reportlab Pillow python-dotenv pydantic

# 4. Uygulama kodunu ZIP'ten çıkar
# (zip'i /tmp/hazarddesk_api.zip olarak yükleyin)
if [ -f /tmp/hazarddesk_api.zip ]; then
    unzip -o /tmp/hazarddesk_api.zip -d /tmp/
    cp -r /tmp/hazarddesk_deploy/* $APP_DIR/
    echo "✓ Uygulama kodu kopyalandı"
fi

# 5. Systemd servis
cat > /etc/systemd/system/sdspass-api.service << 'SERVICE'
[Unit]
Description=SDSPass PDF API
After=network.target

[Service]
User=hazarddesk
WorkingDirectory=/home/hazarddesk/app
Environment="PATH=/home/hazarddesk/venv/bin"
ExecStart=/home/hazarddesk/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable sdspass-api
systemctl start sdspass-api
echo "✓ API servisi başlatıldı"

# 6. Static dosyalar dizini
mkdir -p /var/www/sdspass
echo "✓ Static dizin hazır: /var/www/sdspass"

echo ""
echo "=== Deploy tamamlandı ==="
echo "Şimdi 03_nginx_ssl.sh çalıştırın"
