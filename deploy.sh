#!/usr/bin/env bash
# Setup bot Hermes di VPS Ubuntu/Debian. Jalankan sebagai root:
#   sudo bash deploy.sh https://github.com/USERNAME/hermes-bot.git
#
# Aman dijalankan ulang: dipakai lagi untuk update ke versi terbaru.

set -euo pipefail

REPO_URL="${1:-}"
APP_DIR=/opt/hermes-bot
APP_USER=hermes
SERVICE=hermes-bot

if [[ $EUID -ne 0 ]]; then
  echo "Jalankan sebagai root: sudo bash deploy.sh <url-repo>" >&2
  exit 1
fi

if [[ -z "$REPO_URL" && ! -d "$APP_DIR/.git" ]]; then
  echo "Pemakaian: sudo bash deploy.sh https://github.com/USERNAME/hermes-bot.git" >&2
  exit 1
fi

echo "==> Memasang paket yang dibutuhkan"
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip git

if ! id "$APP_USER" &>/dev/null; then
  echo "==> Membuat user sistem '$APP_USER'"
  useradd --system --create-home --home-dir "/home/$APP_USER" --shell /usr/sbin/nologin "$APP_USER"
fi

# Direktori ini dimiliki user 'hermes' tapi skrip jalan sebagai root, jadi git
# menolaknya sebagai "dubious ownership". Flag -c dipasang per-perintah supaya
# tidak bergantung pada file config mana pun (--global di balik sudo tidak andal
# karena HOME bisa berbeda antar-sesi).
GIT=(git -c "safe.directory=$APP_DIR")

if [[ -d "$APP_DIR/.git" ]]; then
  echo "==> Mengambil versi terbaru"
  "${GIT[@]}" -C "$APP_DIR" fetch --quiet origin
  "${GIT[@]}" -C "$APP_DIR" remote set-head origin --auto >/dev/null 2>&1 || true
  BRANCH=$("${GIT[@]}" -C "$APP_DIR" symbolic-ref --short -q refs/remotes/origin/HEAD || echo origin/main)
  "${GIT[@]}" -C "$APP_DIR" reset --hard --quiet "$BRANCH"
else
  echo "==> Meng-clone repo"
  git clone --quiet "$REPO_URL" "$APP_DIR"
fi

echo "==> Menyiapkan virtualenv"
if [[ ! -x "$APP_DIR/.venv/bin/python" ]]; then
  python3 -m venv "$APP_DIR/.venv"
fi
"$APP_DIR/.venv/bin/pip" install --quiet --upgrade pip
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt"

if [[ ! -f "$APP_DIR/.env" ]]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  echo
  echo "!! $APP_DIR/.env masih kosong."
  echo "!! Isi DISCORD_TOKEN dan NOUS_API_KEY dulu:  sudo nano $APP_DIR/.env"
  echo "!! Lalu jalankan lagi: sudo bash deploy.sh"
  NEEDS_ENV=1
fi

echo "==> Mengatur kepemilikan dan izin"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"
chmod 600 "$APP_DIR/.env"

echo "==> Memasang service systemd"
install -m 644 "$APP_DIR/$SERVICE.service" "/etc/systemd/system/$SERVICE.service"
systemctl daemon-reload
systemctl enable --quiet "$SERVICE"

if [[ -n "${NEEDS_ENV:-}" ]]; then
  echo "==> Service terpasang tapi belum dijalankan (menunggu .env diisi)"
  exit 0
fi

echo "==> Menjalankan ulang bot"
systemctl restart "$SERVICE"
sleep 3
systemctl --no-pager --lines=20 status "$SERVICE" || true

echo
echo "Selesai. Lihat log langsung dengan:  journalctl -u $SERVICE -f"
