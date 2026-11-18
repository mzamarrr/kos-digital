# Kos Digital — Indekos Saung Neglasari

Aplikasi web responsif untuk mengelola kamar, penghuni, tagihan bulanan otomatis, pengingat WhatsApp, dan verifikasi bukti bayar.
Dibuat mengikuti makalah Analis (Analis-UTS) dan slide presentasinya.

## Tech stack
| Keputusan | Pilihan | Alasan singkat |
|-----------|---------|----------------|
| Back-end & API | Python 3 + Flask (monolit, route REST) | Sederhana, route per-role mudah ditegakkan |
| Basis data | SQLite | Mendukung FK, `UNIQUE`, transaksi (NFR-03); tanpa server terpisah |
| Front-end | HTML + JS murni, CSS responsif | Satu halaman, tanpa build step |
| Penjadwal | `app/scheduler.py` (proses terpisah) | Memanggil fungsi layanan yang sama dengan endpoint |
| Hash sandi | scrypt (N=2^17, r=8, p=1) + salt unik | Opsi OWASP bila Argon2id tidak tersedia |
| Token | JWT (HS256), stateless | Sesuai batasan REST stateless |

## Menjalankan
```bash
pip install -r requirements.txt
export KOS_SECRET="$(python -c 'import secrets;print(secrets.token_hex(32))')"
python seed.py            # data FIKTIF: admin/admin12345, budi/budi12345, sari/sari12345
flask --app app run       # buka http://127.0.0.1:5000
python -m app.scheduler --once   # tagihan bulan ini + pengingat (pasang di cron untuk harian)
python -m unittest discover -s tests -v
```

## Struktur
```
app/schema.sql         6 tabel (pengguna, kamar, penghuni, tagihan, pembayaran, log_pesan)
app/api.py             endpoint E-01..E-10 + pendukung
app/services/billing.py   aturan tagihan, idempoten, mesin status, rekap
app/services/reminders.py job pengingat (terpisah dari pembuatan tagihan)
app/services/wa.py     adaptor pengiriman (manual / meta_cloud)
app/scheduler.py       penjadwal
docs/kontrak-api.md    kontrak API (harus sama dengan implementasi)
tests/test_api.py      tes otomatis
```

## Parameter yang MASIH menunggu keputusan pengelola (config.py / env)
`KOS_CYCLE` (calendar | per_penghuni) · `KOS_DUE_DAY` · `KOS_PRORATA` · `KOS_REMIND_DAYS` · batas unggah.
Tarif memakai tarif per kamar (`kamar.tarif`) sebagai asumsi.

## Pengiriman WhatsApp — status jujur
- **manual** (default): sistem menyiapkan teks, admin menekan tombol Kirim (tautan `wa.me`). Selalu bisa.
- **meta_cloud**: jalur resmi WhatsApp Business Platform. **BELUM DIUJI** (butuh akun Meta, template disetujui, opt-in).
  Jangan menulis "pesan WhatsApp berhasil terkirim" di laporan sebelum ada bukti uji kirim.
- Library tidak resmi sengaja tidak dipakai (risiko blokir nomor, R-02).

## Catatan produksi & Deploy
> ⚠️ **PERINGATAN KRITIS KEAMANAN (`KOS_SECRET`)**:
> Di lingkungan produksi atau hosting publik (Render, PythonAnywhere, VPS), variabel lingkungan **`KOS_SECRET` WAJIB DISETEL**.
> Jika `KOS_SECRET` tidak disetel, aplikasi akan membuat kunci acak baru di memori setiap kali worker WSGI (Gunicorn) baru dijalankan atau restart.
> **Akibatnya token JWT pengguna menjadi TIDAK STABIL dan pengguna akan sering terlempar/logout sendiri** ketika request diarahkan ke worker yang berbeda.
> 
> Generate kunci sebelum deploy:
> ```bash
> python -c "import secrets; print(secrets.token_hex(32))"
> ```

Panduan lengkap langkah demi langkah deploy ke **Render** dan **PythonAnywhere** dapat dibaca pada berkas [DEPLOY.md](DEPLOY.md).

Untuk mengembalikan database ke kondisi awal sebelum presentasi di depan dosen:
```bash
python reset_demo.py
```
