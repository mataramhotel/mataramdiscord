# Menghubungkan bot ke akun Hermes kamu

Akun Hermes kamu adalah langganan **Nous Portal**. Portal tidak memakai API key statis — otentikasinya OAuth, dan token disimpan di mesin kamu. Supaya bot Discord bisa ikut memakainya, Nous menyediakan **subscription proxy**: server lokal OpenAI-compatible yang memasang kredensial asli ke tiap request, dan me-refresh-nya sendiri saat mau kedaluwarsa.

Jadi rantainya:

```
bot.py  →  http://127.0.0.1:8645/v1  →  Nous Portal  →  Hermes-4-70B
           (proxy, pegang kredensial)
```

Bot tidak pernah menyentuh kredensial Portal. Di `.env` cukup isi `NOUS_API_KEY=sk-unused` — proxy mengabaikan header itu dan menempelkan yang asli.

## 1. Pastikan punya langganan

Daftar di [portal.nousresearch.com/manage-subscription](https://portal.nousresearch.com/manage-subscription). Hermes-4-70B dan Hermes-4-405B termasuk di dalamnya dengan tarif diskon.

## 2. Pasang Hermes CLI di VPS

```bash
sudo -u hermes -H bash -c 'curl -fsSL https://hermes-agent.nousresearch.com/install.sh | sh'
which hermes    # catat path-nya, dipakai di langkah 5
```

Kalau path-nya bukan `/usr/local/bin/hermes`, sesuaikan `ExecStart` di `hermes-proxy.service`.

## 3. Login OAuth dari VPS headless

Ini bagian yang paling merepotkan: OAuth butuh browser, tapi callback-nya mendarat di loopback **VPS**, bukan laptopmu. Solusinya SSH port forwarding — sambungkan ulang dengan `-L`, jalankan login, lalu buka URL yang muncul di browser laptopmu.

```bash
ssh -L 8765:127.0.0.1:8765 root@ALAMAT_IP_VPS
sudo -u hermes -H hermes portal
```

Perhatikan port callback yang dicetak Hermes saat perintah itu jalan. Kalau bukan 8765, keluar dari SSH dan sambung ulang dengan port yang benar. Detail dan variasinya ada di [panduan OAuth over SSH](https://hermes-agent.nousresearch.com/docs/guides/oauth-over-ssh).

Cek hasilnya:

```bash
sudo -u hermes -H hermes portal info
```

Harus muncul `Auth: ✓ logged in`. Token tersimpan di `/home/hermes/.hermes/auth.json`.

> Kalau kamu terlanjur login sebagai root, tokennya ada di `/root/.hermes`. Pindahkan:
> ```bash
> sudo cp -r /root/.hermes /home/hermes/ && sudo chown -R hermes:hermes /home/hermes/.hermes
> ```

## 4. Jalankan proxy sebagai service

```bash
sudo install -m 644 /opt/hermes-bot/hermes-proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now hermes-proxy
sudo systemctl status hermes-proxy
```

Uji langsung:

```bash
curl -s http://127.0.0.1:8645/v1/models -H "Authorization: Bearer x" | head
```

Kalau keluar daftar model, proxy sudah jalan. Pakai ID model dari situ untuk `HERMES_MODEL`.

## 5. Arahkan bot ke proxy

```bash
sudo nano /opt/hermes-bot/.env
```

```
NOUS_BASE_URL=http://127.0.0.1:8645/v1
NOUS_API_KEY=sk-unused
HERMES_MODEL=Hermes-4-70B
```

Lalu:

```bash
sudo systemctl restart hermes-bot
journalctl -u hermes-bot -f
```

Tag botnya di Discord. Selesai.

## Kalau tidak mau pakai proxy

Kalau kamu punya API key statis dari Nous — atau mau lewat penyedia lain yang juga menghosting Hermes seperti OpenRouter — lewati langkah 2–4 dan isi `.env` langsung:

```
NOUS_BASE_URL=https://inference-api.nousresearch.com/v1
NOUS_API_KEY=api-key-aslimu
```

Kodenya tidak berubah, karena semuanya bicara protokol OpenAI yang sama.

## Kalau bermasalah

| Gejala | Penyebab biasanya |
|---|---|
| `Connection refused` di log bot | Proxy mati. `sudo systemctl status hermes-proxy` |
| `not logged in` di `hermes portal info` | OAuth belum selesai, ulangi langkah 3 |
| `re-authentication required` | Refresh token dicabut. Jalankan `sudo -u hermes -H hermes auth add nous` |
| `model not found` | Ambil ID yang benar dari `curl .../v1/models` di langkah 4 |
| Bot balas lambat / `429` | Kena rate limit tier langgananmu. Pantau di portal.nousresearch.com |

## Dua catatan

**Jangan buka proxy ke jaringan luar.** Proxy tidak punya otentikasi sendiri — siapa pun yang bisa menjangkaunya memakai langganan kamu. Biarkan terikat di `127.0.0.1` seperti konfigurasi bawaan; bot jalan di mesin yang sama jadi tidak perlu diekspos.

**Kuota dibagi.** Proxy memakai satu bearer dengan kuota penuh langgananmu. Kalau bot ramai dipakai, batasnya kena bersama pemakaian Hermes CLI-mu sendiri.
