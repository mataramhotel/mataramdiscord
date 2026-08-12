# Menjalankan bot 24 jam di VPS

Hasil akhir: bot jalan sebagai service systemd — otomatis hidup lagi kalau crash, koneksi putus, atau VPS di-reboot.

## 1. Push kode ke GitHub

Dari folder bot di komputermu:

```bash
cd ~/hermes-bot
git init
git add .
git commit -m "Bot Discord dengan Hermes"
```

Buat repo kosong di [github.com/new](https://github.com/new) — **jangan** centang "Add a README". Lalu:

```bash
git remote add origin https://github.com/USERNAME/hermes-bot.git
git branch -M main
git push -u origin main
```

Sebelum push, pastikan `.env` tidak ikut:

```bash
git status --short | grep -c '\.env$'
```

Harus menghasilkan `0`. File `.gitignore` sudah memblokirnya, tapi kalau `.env` sempat ter-commit, token Discord dan API key-mu bocor — reset keduanya di portal masing-masing dan buat repo baru.

Repo boleh publik; yang rahasia hanya `.env`, dan itu tidak ikut.

## 2. Siapkan VPS

Buat VPS Ubuntu 22.04 atau 24.04 di penyedia mana pun (Hetzner, DigitalOcean, Contabo, Biznet). Spek terkecil sudah cukup — bot ini pakai sekitar 100 MB RAM karena semua kerja berat ada di server Nous.

Login:

```bash
ssh root@ALAMAT_IP_VPS
```

## 3. Deploy

```bash
curl -fsSL https://raw.githubusercontent.com/USERNAME/hermes-bot/main/deploy.sh -o deploy.sh
sudo bash deploy.sh https://github.com/USERNAME/hermes-bot.git
```

Skrip akan memasang Python, membuat user khusus `hermes`, meng-clone repo ke `/opt/hermes-bot`, membuat virtualenv, dan memasang service.

Di akhir dia berhenti dan minta kamu mengisi kredensial:

```bash
sudo nano /opt/hermes-bot/.env      # isi DISCORD_TOKEN dan NOUS_API_KEY
sudo bash deploy.sh                 # jalankan lagi, kali ini bot langsung start
```

Kalau statusnya `active (running)` dan bot muncul online di Discord, selesai.

## Perintah harian

| Tujuan | Perintah |
|---|---|
| Lihat log langsung | `journalctl -u hermes-bot -f` |
| Cek status | `systemctl status hermes-bot` |
| Restart | `sudo systemctl restart hermes-bot` |
| Matikan sementara | `sudo systemctl stop hermes-bot` |
| Matikan permanen | `sudo systemctl disable --now hermes-bot` |
| Ubah konfigurasi | `sudo nano /opt/hermes-bot/.env` lalu restart |

## Update kode

Push perubahan dari komputer, lalu di VPS:

```bash
sudo bash /opt/hermes-bot/deploy.sh
```

Skrip menarik commit terbaru, memperbarui dependensi, dan me-restart bot. File `.env` tidak tersentuh.

## Sedikit pengamanan VPS

Opsional tapi disarankan, terutama kalau VPS-nya publik:

```bash
sudo apt install -y ufw fail2ban
sudo ufw allow OpenSSH && sudo ufw --force enable
sudo apt install -y unattended-upgrades   # patch keamanan otomatis
```

Bot tidak membuka port apa pun — dia hanya menghubungi Discord dan Nous keluar — jadi tidak ada yang perlu di-forward.

## Kalau bermasalah

**`Failed to start` / bot langsung mati** — baca sebabnya:

```bash
journalctl -u hermes-bot -n 50 --no-pager
```

`KeyError: 'DISCORD_TOKEN'` berarti `.env` belum terisi. `LoginFailure` berarti tokennya salah atau sudah di-reset. `401` dari Nous berarti API key-nya yang bermasalah.

**Bot online tapi diam** — Message Content Intent belum aktif di Developer Portal. Aktifkan, lalu `sudo systemctl restart hermes-bot`.

**Sempat jalan lalu berhenti sendiri** — `systemctl status hermes-bot` akan menampilkan `start request repeated too quickly` kalau bot crash berulang. Perbaiki penyebabnya di log, lalu `sudo systemctl reset-failed hermes-bot && sudo systemctl start hermes-bot`.
