# Menghubungkan bot ke akun Hermes kamu

Akun Hermes kamu adalah langganan **Nous Portal**. Portal tidak memakai API key statis — otentikasinya OAuth, dan token disimpan di mesin kamu. Supaya bot Discord bisa ikut memakainya, Nous menyediakan **subscription proxy**: server lokal OpenAI-compatible yang memasang kredensial asli ke tiap request dan me-refresh-nya sendiri.

```
bot.py  →  http://127.0.0.1:8645/v1  →  Nous Portal  →  model
           (proxy, pegang kredensial)
```

Bot tidak pernah menyentuh kredensial Portal. Di `.env` cukup isi `NOUS_API_KEY=sk-unused` — proxy mengabaikan header itu dan menempelkan yang asli.

Langkah-langkah di bawah sudah diverifikasi di Ubuntu, bukan dari dokumentasi saja.

## 1. Pasang Hermes CLI

Sebagai user login biasa, **tanpa `sudo`** — supaya terpasang di home-mu sendiri, tempat token OAuth akan disimpan:

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
source ~/.bashrc
which hermes
```

Hasil `which hermes` biasanya `/home/NAMAUSER/.local/bin/hermes` — bukan `/usr/local/bin`. Catat, dipakai di langkah 3.

## 2. Login ke Nous Portal

```bash
hermes portal
```

Hermes memakai alur **kode perangkat**, jadi tidak perlu SSH port forwarding meski VPS-mu tanpa browser. Dia mencetak URL beserta kode seperti `FLR9-7P2L`; buka URL itu di browser laptopmu, setujui, dan terminal akan otomatis lanjut sendiri.

Selesai kalau muncul `Login successful!` dan token tersimpan di `~/.hermes/auth.json`.

Cek kapan saja:

```bash
hermes proxy status     # harus: [nous] Nous Portal — ready
```

> Hermes juga akan menawarkan model default untuk CLI-nya sendiri. Pilihan itu tidak berpengaruh ke bot Discord — bot membaca `.env`, bukan config Hermes.

## 3. Jalankan proxy sebagai service

Ganti `NAMAUSER` dengan user login kamu di kedua tempat, dan sesuaikan path `hermes` dengan hasil langkah 1:

```bash
sudo tee /etc/systemd/system/hermes-proxy.service > /dev/null <<'EOF'
[Unit]
Description=Hermes subscription proxy (Nous Portal)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=NAMAUSER
WorkingDirectory=/home/NAMAUSER
Environment=HOME=/home/NAMAUSER
ExecStart=/home/NAMAUSER/.local/bin/hermes proxy start --host 127.0.0.1 --port 8645
Restart=always
RestartSec=5
SyslogIdentifier=hermes-proxy

[Install]
WantedBy=multi-user.target
EOF

ls -l /etc/systemd/system/hermes-proxy.service    # pastikan benar-benar jadi
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-proxy
systemctl status hermes-proxy --no-pager
```

Proxy harus dijalankan sebagai user yang tadi login OAuth — dia membaca `~/.hermes/auth.json` milik user itu. Jangan pakai user sistem `hermes` yang dibuat `deploy.sh`; user itu sengaja tanpa shell.

## 4. Cari ID model yang benar

Portal memakai format slug (`vendor/model`), bukan nama pendek seperti `Hermes-4-70B`:

```bash
curl -s http://127.0.0.1:8645/v1/models -H "Authorization: Bearer x" \
  | python3 -c "import sys,json;[print(m['id']) for m in json.load(sys.stdin)['data'] if 'hermes' in m['id'].lower()]"
```

Hapus bagian `if 'hermes' ...` untuk melihat seluruh katalog.

## 5. Arahkan bot ke proxy

```bash
sudo nano /opt/hermes-bot/.env
```

```
NOUS_BASE_URL=http://127.0.0.1:8645/v1
NOUS_API_KEY=sk-unused
HERMES_MODEL=<id dari langkah 4>
```

```bash
sudo systemctl restart hermes-bot
journalctl -u hermes-bot -f
```

Muncul `Login sebagai <nama-bot>` = selesai. Tag botnya di Discord.

## Kalau bermasalah

| Gejala | Penyebab biasanya |
|---|---|
| `Unit hermes-proxy.service could not be found` | Blok `tee` di langkah 3 tidak tersalin utuh. Cek dengan `ls -l` |
| `curl` balas kosong | Proxy mati. `systemctl status hermes-proxy` |
| `Connection refused` di log bot | Sama seperti di atas |
| `not logged in` di `hermes proxy status` | OAuth belum selesai, ulangi langkah 2 |
| `re-authentication required` | Refresh token dicabut. Jalankan `hermes portal` lagi |
| `model not found` | ID model salah, ulangi langkah 4 |
| Bot lambat atau `429` | Kena rate limit tier langgananmu |

## Dua catatan

**Jangan buka proxy ke jaringan luar.** Proxy tidak punya otentikasi sendiri — siapa pun yang menjangkaunya memakai langgananmu. Biarkan terikat di `127.0.0.1`; bot jalan di mesin yang sama jadi tidak perlu diekspos.

**Kuota dibagi.** Proxy memakai satu bearer dengan kuota penuh langgananmu, bersama pemakaian Hermes CLI-mu sendiri.
