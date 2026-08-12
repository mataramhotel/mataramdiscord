# Bot Discord dengan model Hermes

Bot yang membalas ketika di-tag di channel, jawabannya dihasilkan model Hermes dari Nous Research lewat endpoint OpenAI-compatible.

## 1. Siapkan aplikasi Discord

Di [Developer Portal](https://discord.com/developers/applications), pilih aplikasimu:

- **Bot** → **Reset Token** → salin token → isi `DISCORD_TOKEN`
- **Bot** → **Privileged Gateway Intents** → aktifkan **Message Content Intent**. Tanpa ini `message.content` selalu kosong dan bot tidak akan pernah membalas.
- **Installation** → salin install link → buka di browser → **Add to server**

Permission minimal yang dibutuhkan bot di server: View Channels, Send Messages, Read Message History.

## 2. Ambil API key Hermes

Buat key di [portal.nousresearch.com](https://portal.nousresearch.com/manage-subscription), isi ke `NOUS_API_KEY`.

Model Nous saat ini: `Hermes-4.3-36B`, `Hermes-4-70B`, `Hermes-4-405B` (konteks 128K). ID persis di API bisa berbeda — jalankan `python list_models.py` untuk melihat daftar sebenarnya, lalu set `HERMES_MODEL` sesuai hasilnya.

## 3. Jalankan

```bash
pip install -r requirements.txt
cp .env.example .env      # lalu isi DISCORD_TOKEN dan NOUS_API_KEY
python bot.py
```

Kalau berhasil, log menampilkan `Login sebagai <nama-bot>` dan status bot berubah jadi online.

## Cara pakai

| Aksi | Hasil |
|---|---|
| `@bot apa itu quantum computing?` | Bot membalas di channel yang sama |
| `@bot reset` | Hapus riwayat percakapan di channel itu |

Riwayat disimpan per channel, 8 giliran terakhir (atur lewat `HISTORY_TURNS`). Semua di memori — restart bot berarti riwayat hilang.

## Konfigurasi

Semua lewat `.env`:

| Variabel | Default | Fungsi |
|---|---|---|
| `HERMES_MODEL` | `Hermes-4-70B` | ID model |
| `SYSTEM_PROMPT` | (lihat `bot.py`) | Kepribadian bot |
| `HISTORY_TURNS` | `8` | Jumlah giliran yang diingat |
| `MAX_TOKENS` | `800` | Panjang maksimal jawaban |
| `TEMPERATURE` | `0.7` | Kreativitas jawaban |
| `NOUS_BASE_URL` | `https://inference-api.nousresearch.com/v1` | Ganti kalau mau pakai provider lain (OpenRouter, Ollama, vLLM) |

Karena endpointnya OpenAI-compatible, mengarahkan `NOUS_BASE_URL` ke OpenRouter atau server lokal (Ollama/vLLM) cukup dengan mengganti base URL dan key — kodenya tidak berubah.

## Masalah umum

**Bot online tapi diam saja** — Message Content Intent belum aktif, atau bot tidak punya permission Send Messages di channel itu.

**`401` / `invalid api key`** — key salah atau subscription belum aktif.

**`model not found`** — jalankan `list_models.py` dan pakai ID yang muncul di sana.

**Jawaban terpotong** — naikkan `MAX_TOKENS`. Jawaban di atas 2000 karakter otomatis dipecah jadi beberapa pesan.
