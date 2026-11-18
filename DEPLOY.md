# Panduan Deploy — Kos Digital

Dokumen ini memandu langkah deploy aplikasi Kos Digital ke layanan cloud publik (NFR-05, kewajiban demo UTS).

---

## ⚠️ Peringatan Kritis Keamanan: `KOS_SECRET`

Aplikasi menggunakan PyJWT untuk autentikasi stateless.
* **Jika `KOS_SECRET` tidak disetel di environment produksi**, sistem akan membuat kunci acak baru setiap kali proses/worker WSGI baru dijalankan atau restart.
* Akibatnya: **Token login pengguna akan langsung tidak valid (tidak stabil/sering logout sendiri)** saat berpindah worker Gunicorn.
* **Solusi**: Buat string rahasia 64-karakter sekali saja, lalu pasang di Environment Variables hosting:
  ```bash
  python -c "import secrets; print(secrets.token_hex(32))"
  ```

---

## Pilihan 1: Render.com (Direkomendasikan — Paling Praktis via GitHub)

Render terhubung langsung ke repositori GitHub Anda dan otomatis mendeteksi konfigurasi melalui `Procfile`.

### Langkah-langkah:
1. Daftar atau login di [https://render.com](https://render.com).
2. Di dashboard, klik tombol **New +** lalu pilih **Web Service**.
3. Pilih opsi **Build and deploy from a Git repository**, lalu hubungkan repositori GitHub `kos-digital` Anda.
4. Isi konfigurasi berikut:
   * **Name**: `kos-digital` (atau nama unik Anda)
   * **Region**: Singapore (Southeast Asia) agar akses cepat dari Indonesia
   * **Branch**: `main` (atau `dev`)
   * **Root Directory**: Biarkan kosong (jika repo berisi root proyek)
   * **Runtime**: `Python 3`
   * **Build Command**:
     ```bash
     pip install -r requirements.txt && python seed.py
     ```
   * **Start Command**:
     ```bash
     gunicorn "app:create_app()"
     ```
   * **Instance Type**: `Free`
5. Gulir ke bawah ke bagian **Environment Variables**, klik **Add Environment Variable**:
   * Key: `KOS_SECRET`
   * Value: `<masukkan hasil generate token acak 64 karakter>`
   * *(Opsional)* Key: `KOS_ADMIN_PW`, Value: `admin12345` (atau sandi admin pilihan Anda)
   * *(Opsional)* Key: `KOS_WA`, Value: `manual`
6. Klik **Create Web Service**. Tunggu proses build selesai (sekitar 2–3 menit).
7. Setelah status menjadi **Live**, salin URL publik yang disediakan (contoh: `https://kos-digital-xxxx.onrender.com`).

---

## Pilihan 2: PythonAnywhere (Alternatif Tanpa Kartu Kredit)

PythonAnywhere menyediakan hosting Python gratis dengan kontrol manual WSGI.

### Langkah-langkah:
1. Daftar akun gratis di [https://www.pythonanywhere.com](https://www.pythonanywhere.com).
2. Buka tab **Consoles** -> jalankan **Bash console**:
   ```bash
   git clone <URL_REPO_GITHUB_ANDA> kos-digital
   cd kos-digital
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   export KOS_SECRET="masukkan_string_rahasia_anda"
   python seed.py
   ```
3. Buka tab **Web** di dashboard PythonAnywhere:
   * Klik **Add a new web app** -> pilih **Manual configuration** -> pilih **Python 3.10 / 3.11**.
   * Di bagian **Virtualenv**, masukkan path: `/home/<username>/kos-digital/.venv`
   * Di bagian **Code**:
     * Source code: `/home/<username>/kos-digital`
     * Working directory: `/home/<username>/kos-digital`
4. Di bagian **Code**, klik tautan konfigurasi **WSGI configuration file** (misal `/var/www/<username>_pythonanywhere_com_wsgi.py`), hapus isinya dan ganti dengan:
   ```python
   import sys
   import os

   path = '/home/<username>/kos-digital'
   if path not in sys.path:
       sys.path.append(path)

   # Set environment variables produksi
   os.environ['KOS_SECRET'] = 'masukkan_string_rahasia_anda'
   os.environ['KOS_WA'] = 'manual'

   from app import create_app
   application = create_app()
   ```
5. Klik **Save**, kembali ke tab Web, lalu klik tombol hijau **Reload <username>.pythonanywhere.com**.
6. Akses URL: `https://<username>.pythonanywhere.com`.

---

## 📌 Catatan Basis Data & Bukti Unggahan pada Hosting Gratis

* Paket hosting gratis (Render / Railway) menggunakan *ephemeral filesystem*. Artinya, jika server tidur (*idle sleep*) atau di-restart, berkas `kos.db` dan folder `uploads/` akan kembali ke kondisi saat build awal (`seed.py`).
* Untuk kebutuhan demo penilaian dosen dan pengujian UTS, kondisi ini **cukup dan aman**.
* Jika ingin mereset data demo saat aplikasi sudah berjalan di cloud, cukup jalankan ulang `python reset_demo.py` di terminal console hosting atau trigger Re-deploy di dashboard Render.
