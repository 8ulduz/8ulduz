#!/usr/bin/env bash
# 8ULDUZ «Dinlə» səs serveri (SARA) — Hetzner serverində quraşdırma və yeniləmə. Təkrar işə salmaq təhlükəsizdir (yeniləyir).
#   curl -fsSL https://raw.githubusercontent.com/8ulduz/8ulduz/main/.github/ses-server/install.sh | sudo bash
# Ubuntu/Debian. Server yalnız 127.0.0.1:8790-da dinləyir (kənardan birbaşa açıq deyil); internetə Cloudflare Tunnel çıxarır.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo "sudo ilə işə salın"; exit 1; }
command -v apt-get >/dev/null || { echo "Bu skript Ubuntu/Debian üçündür"; exit 1; }

DIR=/opt/8ulduz-ses CACHE=/var/cache/8ulduz-ses RAW=https://raw.githubusercontent.com/8ulduz/8ulduz/main
mem=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
echo "== 8ulduz ses: yaddaş ${mem} MB, prosessor $(nproc)"
[ "$mem" -ge 1500 ] || echo "!! Yaddaş azdır (model ~1 GB istəyir): server yavaş ola bilər"

echo "== Paketlər"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3 python3-venv ffmpeg curl >/dev/null

id ses >/dev/null 2>&1 || useradd --system --home "$DIR" --shell /usr/sbin/nologin ses
mkdir -p "$DIR" "$CACHE"
echo "== Kod"
for f in .github/ses-server/server.py .github/ses-server/az_text.py reader_content.py; do
  curl -fsSL "$RAW/$f?t=$(date +%s)" -o "$DIR/$(basename "$f")"
done

echo "== Python mühiti (ilk dəfə bir neçə dəqiqə)"
[ -x "$DIR/venv/bin/python" ] || python3 -m venv "$DIR/venv"
"$DIR/venv/bin/pip" install -q --upgrade pip
"$DIR/venv/bin/pip" install -q torch --index-url https://download.pytorch.org/whl/cpu
"$DIR/venv/bin/pip" install -q transformers numpy
chown -R ses:ses "$DIR" "$CACHE"

cat > /etc/systemd/system/8ulduz-ses.service <<UNIT
[Unit]
Description=8ULDUZ Dinlə səs serveri (SARA)
After=network-online.target
Wants=network-online.target

[Service]
User=ses
WorkingDirectory=$DIR
Environment=SES_CACHE=$CACHE HF_HOME=$DIR/hf PYTHONUNBUFFERED=1
ExecStart=$DIR/venv/bin/python $DIR/server.py
Restart=always
RestartSec=5
Nice=5

[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now 8ulduz-ses >/dev/null
systemctl restart 8ulduz-ses

echo "== Model yüklənir (ilk dəfə ~150 MB)"
for i in $(seq 1 90); do
  curl -fs http://127.0.0.1:8790/saglam >/dev/null 2>&1 && break
  sleep 5
done
if curl -fs http://127.0.0.1:8790/saglam >/dev/null; then
  echo "== HAZIR: səs serveri işləyir (127.0.0.1:8790)"
  echo "   Növbəti addım: Cloudflare Tunnel ilə ses.8ulduz.az → http://localhost:8790"
else
  echo "!! Server cavab vermir. Jurnal: journalctl -u 8ulduz-ses -n 50"
  exit 1
fi
