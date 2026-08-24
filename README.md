# 📰 Web3 News Bot (Telegram)

Bot Telegram yang **membaca data pasar Web3 secara real-time**, lalu memakai AI (Claude)
untuk menulis **3 angle postingan** siap-bagikan ke **X (Twitter)** dan **Facebook**.
Bot juga **belajar dari feedback 👍/👎** kamu, sehingga gaya postingan makin sesuai
selera audiens seiring waktu.

---

## ✨ Fitur

- **3 angle sekaligus** tiap generasi: 📊 Analitis, 🚨 Dramatis, 🎓 Edukatif.
- **Dua versi per angle**: versi X (≤280 karakter) & versi Facebook (lebih panjang & terstruktur).
- **Feedback loop (belajar)**: tombol 👍/👎 menyimpan gaya favoritmu dan menjadikannya
  contoh untuk postingan berikutnya (`feedback.json`).
- **Data pasar mendalam** (semua API publik, tanpa API key):
  - Harga & perubahan 24 jam, koin trending, top gainers/losers — CoinGecko
  - Total market cap, volume, dominasi BTC/ETH — CoinGecko
  - Fear & Greed Index — alternative.me
  - Funding rate perpetual BTC/ETH — Binance Futures
  - Total TVL DeFi — DefiLlama
  - Headline berita kripto terbaru — RSS Cointelegraph
- **Tombol share** langsung ke X & Facebook + blok teks yang bisa di-copy (tekan-tahan).

---

## 🧩 Perintah Bot

| Perintah | Fungsi |
|----------|--------|
| `/start`, `/help` | Tampilkan bantuan |
| `/berita`, `/news` | Buat 3 angle postingan dari data terkini |
| `/trending` | Lihat koin yang sedang trending |
| `/stats` | Lihat jumlah feedback 👍/👎 yang terkumpul |

---

## 🚀 Cara Menjalankan

### 1. Prasyarat
- Python 3.10+ (diuji pada Python 3.13)
- Token bot Telegram dari [@BotFather](https://t.me/BotFather)
- Key gateway Anthropic (GoRouter)

### 2. Install dependency
```bash
pip install -r requirements.txt
```

### 3. Siapkan konfigurasi
Salin `.env.example` menjadi `.env`, lalu isi nilainya:
```bash
cp .env.example .env
```
```dotenv
ANTHROPIC_AUTH_TOKEN=<key-gateway-kamu>
ANTHROPIC_BASE_URL=https://gorouter.app
ANTHROPIC_MODEL=claude-opus-4-8
TELEGRAM_BOT_TOKEN=<token-dari-BotFather>
POST_LANG=id          # id = Indonesia, en = English
```

### 4. Jalankan
```bash
python bot.py
```
Buka bot di Telegram, kirim `/start`, lalu `/berita`.

---

## ☁️ Deploy ke Railway (always-on)

Bot ini memakai **long polling**, jadi butuh host yang menyala 24/7 (Railway cocok —
**bukan** Vercel/Netlify yang serverless & tidak bisa menjalankan proses polling terus-menerus).

1. Push proyek ini ke GitHub (pastikan `.env` **tidak** ikut — sudah diatur di `.gitignore`).
2. Di [railway.app](https://railway.app): **New Project → Deploy from GitHub repo** → pilih repo ini.
3. Buka tab **Variables**, tambahkan variabel (nilai diambil dari `.env` lokalmu):
   - `ANTHROPIC_AUTH_TOKEN`
   - `ANTHROPIC_BASE_URL` = `https://gorouter.app`
   - `ANTHROPIC_MODEL` = `claude-opus-4-8`
   - `TELEGRAM_BOT_TOKEN`
   - `POST_LANG` = `id`
4. Railway otomatis membaca `railway.json` / `Procfile` dan menjalankan `python bot.py`.
5. (Opsional, agar feedback 👍/👎 tidak hilang saat redeploy) tambahkan **Volume**,
   mount di `/data`, lalu set variabel `DATA_DIR=/data`.

> Tanpa Volume, file `feedback.json` bersifat sementara dan akan ter-reset setiap redeploy.

---

## 📁 Struktur Proyek

| File | Peran |
|------|-------|
| `bot.py` | Aplikasi Telegram: perintah, tombol share, callback feedback |
| `web3_data.py` | Mengambil & merangkum data pasar Web3 dari berbagai sumber |
| `ai_writer.py` | Memanggil Claude untuk menulis 3 angle postingan |
| `feedback_store.py` | Menyimpan feedback 👍/👎 & menyuntikkan contoh ke prompt |
| `requirements.txt` | Daftar dependency |
| `.env` | Konfigurasi & rahasia (tidak di-commit) |
| `.env.example` | Template konfigurasi tanpa rahasia |
| `feedback.json` | Data feedback (dibuat otomatis saat runtime) |
| `Procfile` / `railway.json` | Konfigurasi deploy Railway (`python bot.py`) |
| `.python-version` | Versi Python untuk build Railway |

---

## 🧠 Bagaimana Bot "Belajar"

1. Kamu tekan 👍 pada postingan yang menurutmu bagus → teksnya disimpan sebagai **contoh positif**.
2. Tekan 👎 → dicatat sebagai **gaya yang dihindari**.
3. Saat membuat postingan berikutnya, contoh favoritmu disuntikkan ke prompt AI:
   *"tiru nada, struktur, dan energinya — jangan salin angkanya"*.

Bot **tidak** melakukan fine-tuning model; ia memakai mekanisme *few-shot example* yang
membuat output makin konsisten dengan selera audiensmu.

---

## ⚠️ Catatan

- **Jaga kerahasiaan `.env`.** File ini berisi token bot & key gateway, dan sudah masuk `.gitignore`.
  Jika token bot pernah terekspos, buat ulang lewat @BotFather (`/revoke`).
- **Bukan nasihat finansial.** Postingan bersifat informatif/hiburan; selalu lakukan riset sendiri.
- Beberapa sumber data bersifat *best-effort* — jika satu API sedang tidak dapat diakses
  (mis. funding rate terblokir di jaringan tertentu), bagian itu otomatis dilewati tanpa
  membuat bot error.
- Rate limit CoinGecko gratis terbatas; hindari memanggil `/berita` terlalu sering beruntun.
