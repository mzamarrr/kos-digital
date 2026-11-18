# UI/UX Mamikos Clean Pro Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Meng-upgrade antarmuka web Kos Digital di `app/static/index.html` mengadopsi standar industri Mamikos Clean Pro (Emerald Green + Slate Navy + Stat Cards + Humanized Tenant Portal) dengan mempertahankan 100% kontrak DOM, API, dan kelulusan 43 tes unit.

**Architecture:** Modifikasi satu berkas frontend `app/static/index.html` dengan styling CSS modern (Plus Jakarta Sans, grid, responsive card layouts, soft shadow), penambahan visual stat cards di admin, card-based invoice dan instruksi rekening di portal penghuni, serta modal dialog untuk preview bukti transfer.

**Tech Stack:** HTML5, CSS3 Modern, Vanilla JavaScript (ES6+), Google Fonts (Plus Jakarta Sans).

**Spec:** `docs/superpowers/specs/2026-11-18-ui-ux-mamikos-redesign.md`

## Global Constraints
- Single-file frontend: Hanya memodifikasi `app/static/index.html`. Tidak ada penambahan dependensi npm / build tools.
- DOM & API Compatibility: Mempertahankan semua ID elemen (`#u`, `#p`, `#go`, `#tabs`, `#view`, `#who`, `#logout`, `#toast`, `#per`, `#gen`, `#addk`, `#addp`, `#remind`, `#rp`, `#rk`, `#rkout`) dan data attributes (`data-t`, `data-set`, `data-bukti`, `data-up`, `data-file`, `data-sent`, `data-ke`, `data-kdel`, `data-off`).
- Zero API/DB schema change: Seluruh 43 tes unit harus tetap lulus tanpa perubahan file backend.

## Review Focus
1. Tampilan responsif pada resolusi HP (~390px) tidak boleh ada elemen yang terpotong atau overflow horizontal tak terduga.
2. Form submit dan interaksi tombol (Tambah Kamar, Tambah Penghuni, Buat Tagihan, dsb.) harus tetap memicu handler JavaScript yang sama persis.
3. Unggah bukti pembayaran oleh penghuni dan preview bukti oleh admin harus berfungsi mulus tanpa galat MIME/CORS.
4. Tautan WhatsApp (`wa.me`) pada Tab Pesan harus tetap membuka aplikasi WhatsApp dengan pesan terisi rapi.

---

### Task 1: Redesign CSS & Layout System di `app/static/index.html`
**Files:**
- Modify: `app/static/index.html`

- [ ] **Step 1: Terapkan Google Font Plus Jakarta Sans, Palet Warna Mamikos, dan Komponen Dasar**
  - Terapkan Google Fonts `Plus Jakarta Sans`.
  - Definisikan CSS variables: `--primary: #10b981`, `--primary-dark: #059669`, `--navy: #0f172a`, `--bg: #f8fafc`, `--card: #ffffff`, `--line: #e2e8f0`.
  - Buat komponen card, modern table, pill badges dengan dot indikator (`● Lunas`, `● Menunggu`, `● Ditolak`), dan modal preview dialog.

- [ ] **Step 2: Desain Ulang Header, Login Card, dan Navigasi Segmented Control**
  - Header dengan logo brand, status badge chip pengguna, dan tombol keluar berikon.
  - Form login dengan kartu melayang halus (*soft shadow*) dan tombol emerald.
  - Tab navigasi bergaya *segmented pill control* yang aktif dengan transisi halus.

- [ ] **Step 3: Desain Ulang Tampilan Admin (Tagihan, Kamar, Penghuni, Pesan, Rekap)**
  - Tampilkan Stat Metric Cards di awal Tab Tagihan (Kamar Terisi, Pemasukan, Tunggakan).
  - Tampilkan form Tambah Kamar & Penghuni dalam form card yang terstruktur rapi.
  - Tab Pesan dengan callout instruksi WhatsApp dan tombol Kirim berikon hijau WA.
  - Tab Rekap dengan ringkasan visual dan tabel penunggak.

- [ ] **Step 4: Desain Ulang Tampilan Portal Penghuni (Tagihan Saya & Info Rekening)**
  - Tambahkan kartu panduan transfer bank (BCA / Mandiri a.n Pengelola Kos) lengkap dengan tombol salin nomor rekening.
  - Ubah daftar tagihan menjadi kartu tagihan modern (*invoice cards*) dengan tanggal jatuh tempo yang tegas dan dropzone unggah bukti.

- [ ] **Step 5: Tambahkan Komponen Modal Preview Bukti Transfer**
  - Sediakan elemen modal `<div id="bukti-modal">` di HTML dengan backdrop blur.
  - Perbarui event handler `data-bukti` agar menampilkan gambar/berkas di dalam modal tersebut dengan tombol tutup `✕`.

---

### Task 2: Verifikasi Fungsionalitas & Kelulusan Tes
**Files:**
- Test: `tests/test_api.py`
- Verify: Endpoint lokal `http://127.0.0.1:5000`

- [ ] **Step 1: Jalankan python -m unittest discover -s tests -v**
  - Pastikan semua 43 tes unit lulus tanpa peringatan baru.
- [ ] **Step 2: Verifikasi Alur Login, Unggah Bukti, dan Generate Tagihan**
  - Pastikan tidak ada sintaks JavaScript error di console.

---

### Task 3: Git Commit, Push ke GitHub, dan Deploy ke PythonAnywhere
**Files:**
- Modify: `app/static/index.html`

- [ ] **Step 1: Git commit "Upgrade UI/UX to Mamikos Clean Pro standard"**
- [ ] **Step 2: Push commit ke branch main di GitHub**
- [ ] **Step 3: Berikan panduan git pull & reload di PythonAnywhere agar server online ter-update**
