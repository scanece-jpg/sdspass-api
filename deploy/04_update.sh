#!/bin/bash
# SDSPass — Kod Güncelleme (deploy sonrası güncellemeler için)
# hazarddesk kullanıcısı olarak çalıştır
set -e

APP_DIR="/home/hazarddesk/app"
VENV_DIR="/home/hazarddesk/venv"

echo "=== SDSPass Güncelleme ==="

# Yeni zip varsa güncelle
if [ -f /tmp/hazarddesk_api.zip ]; then
    cd $APP_DIR
    unzip -o /tmp/hazarddesk_api.zip -d /tmp/
    
    # Sadece app/ ve data/ klasörlerini güncelle (config'e dokunma)
    cp -r /tmp/hazarddesk_deploy/app/* $APP_DIR/app/
    cp -r /tmp/hazarddesk_deploy/data/* $APP_DIR/data/ 2>/dev/null || true
    
    echo "✓ Kod güncellendi"
fi

# HTML güncelle
if [ -f /tmp/euh_calculator.html ]; then
    cp /tmp/euh_calculator.html /var/www/sdspass/index.html
    echo "✓ HTML güncellendi"
fi

# Servisi yeniden başlat
sudo systemctl restart sdspass-api
sleep 2

# Sağlık kontrolü
if curl -sf http://127.0.0.1:8000/health > /dev/null; then
    echo "✓ API çalışıyor"
else
    echo "✗ API başlamadı — log kontrol et:"
    echo "  sudo journalctl -u sdspass-api -n 50"
fi

echo "=== Güncelleme tamamlandı ==="
