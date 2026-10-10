"""Danışman hesabı için gizli anahtar üretir ve yerel .env'ye ekler.

Kullanım:  python scripts/hesap_anahtari.py dipol-kimya

Anahtar ekrana yalnız bir kez yazılır. Sunucuda (Render → Environment) aynı satırı
SDSPASS_HESAP_ANAHTARLARI değişkenine ekleyin; birden çok hesap virgülle ayrılır.
"""
import re, secrets, sys
from pathlib import Path

ENV = Path(__file__).resolve().parents[1] / '.env'
VAR = 'SDSPASS_HESAP_ANAHTARLARI'

hesap = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
if not re.match(r'^[a-z0-9][a-z0-9-]{0,59}$', hesap):
    sys.exit('Hesap adı küçük harf, rakam ve tire olmalı (örn. dipol-kimya).')
key = secrets.token_urlsafe(32)
lines = ENV.read_text(encoding='utf-8').splitlines() if ENV.exists() else []
for i, ln in enumerate(lines):
    if ln.startswith(VAR + '='):
        pairs = [p for p in ln.split('=', 1)[1].strip().strip('"').split(',')
                 if p.strip() and not p.strip().startswith(hesap + ':')]
        lines[i] = f'{VAR}=' + ','.join(pairs + [f'{hesap}:{key}'])
        break
else:
    lines.append(f'{VAR}={hesap}:{key}')
ENV.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(f'{hesap} hesabının anahtarı (bir kez gösterilir, güvenli yerde saklayın):\n\n  {key}\n')
print(f'Yerel .env güncellendi. Render → Environment → {VAR} değişkenine şunu ekleyin:\n\n  {hesap}:{key}\n')
print('Panelde "Danışman hesabı" alanına yalnız anahtarı girin.')
