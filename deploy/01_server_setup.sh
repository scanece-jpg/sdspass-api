#!/bin/bash
# HazardDesk — Sunucu İlk Kurulum
# Ubuntu 24.04 LTS | root olarak çalıştır
set -e

echo "=== HazardDesk Sunucu Kurulumu ==="

# 1. Sistem güncelle
apt update && apt upgrade -y

# 2. Gerekli paketler
apt install -y \
    nginx \
    python3.12 python3.12-venv python3-pip \
    postgresql postgresql-contrib \
    redis-server \
    certbot python3-certbot-nginx \
    ufw fail2ban \
    git curl wget unzip \
    fonts-dejavu-core \
    supervisor

# 3. Kullanıcı oluştur (root ile çalışmayacağız)
useradd -m -s /bin/bash hazarddesk || true
usermod -aG sudo hazarddesk

# 4. UFW Firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# 5. Fail2ban
systemctl enable fail2ban
systemctl start fail2ban

# 6. SSH güvenliği (opsiyonel ama önerilen)
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config || true

echo "=== Sunucu kurulumu tamamlandı ==="
echo "Şimdi 02_app_deploy.sh çalıştırın"
