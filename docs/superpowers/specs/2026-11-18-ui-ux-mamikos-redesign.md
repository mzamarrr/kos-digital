# Design Specification: UI/UX Mamikos Clean Pro Upgrade

**Tanggal**: 2026-11-18  
**Topik**: Upgrade UI/UX Kos Digital Bergaya Mamikos Clean Pro  
**Status**: Disetujui Pengguna  

---

## 1. Latar Belakang & Tujuan (Why & Intent)
Tampilan UI/UX awal Kos Digital masih bersifat utilitarian dan mentah. Peningkatan ini bertujuan memberikan antarmuka bertaraf komersial dengan mengadopsi standar industri properti indekos Indonesia (**Mamikos Clean Pro**), sehingga aplikasi tampak elegan, intuitif, dan meyakinkan saat dipresentasikan di hadapan dosen dan rekan mahasiswa.

---

## 2. Sasaran & Batasan (Goals & Non-Goals)

### Goals:
1. **Tipografi & Desain Modern**:
   * Menggunakan font modern *Plus Jakarta Sans* dari Google Fonts.
   * Palet warna bertema properti: *Emerald Green* (`#10b981`), *Deep Slate/Navy* (`#0f172a`), *Clean Off-white* (`#f8fafc`), dan *Warm Gold* (`#f59e0b`).
2. **Dashboard Metric Cards (Admin)**:
   * Menyajikan 4 ringkasan visual instan di bagian atas: *Kamar Terisi*, *Pemasukan Bulan Ini*, *Tunggakan*, dan *Menunggu Verifikasi*.
3. **Portal Penghuni yang Manusiawi**:
   * Menampilkan kartu instruksi rekening transfer bank (BCA / Mandiri / BSI pengelola) sebelum penghuni mengunggah bukti bayar.
   * Tagihan bergaya kartu modern (*invoice card*) yang ramah layar sentuh HP (~390px).
4. **Modal Dialog Bukti Bayar**:
   * Menampilkan popup modal elegan untuk melihat foto bukti pembayaran langsung di layar tanpa melempar admin ke tab baru browser.
5. **Navigasi Segmented Control**:
   * Navigasi tab admin/penghuni yang halus dengan efek aktif yang jelas.

### Non-Goals & Constraints:
* **Zero Backend / API Changes**: Tidak mengubah skema database, rute endpoint API, kode status HTTP, maupun logika layanan backend.
* **Semua 43 Unit Tests Tetap Lulus 100%**: Tidak ada tes yang diubah atau dilemahkan.
* **Single File Frontend**: Tetap berpusat pada satu berkas [app/static/index.html](file:///d:/Pak%20Agus/Manajemen%20%20Proyek/satset%20satset/kos-digital%20satset/kos-digital/app/static/index.html) tanpa dependensi build step (tanpa npm/webpack).
* **DOM Contract Preserved**: Semua `id` elemen (`#u`, `#p`, `#go`, `#tabs`, `#view`, `#per`, `#gen`, `#addk`, `#addp`, `#remind`, `#rp`, `#rk`, `#rkout`) dan data attributes (`data-set`, `data-bukti`, `data-up`, `data-sent`, `data-ke`, `data-kdel`, `data-off`) dipertahankan sepenuhnya.

---

## 3. Pendekatan Desain (Approaches)

* **Opsi A (Dipilih) — Mamikos Clean Pro**:
  * Pendekatan berbasis kartu properti, aksen hijau zamrud & navy, stat cards di dashboard, instruksi transfer rekening bank yang jelas. Sangat cocok dengan mental model dosen dan mahasiswa untuk sistem indekos.
* **Opsi B (Ditolak) — Modern SaaS (Stripe/Linear)**:
  * Terlalu kaku dan dingin (dominasi abu-abu B2B), kurang cocok untuk interaksi penghuni kos awam di HP.

---

## 4. Rincian Komponen Tampilan Baru

1. **Header**: Logo ikon rumah/kos + teks "Kos Digital · Saung Neglasari", chip status pengguna (Admin/Penghuni), dan tombol Keluar modern.
2. **Stat Cards (Admin Dashboard)**: Grid 4 kartu metrik dengan ikon SVG halus dan angka nominal rupiah yang mudah dibaca.
3. **Room Cards & Form**: Input dengan floating label/placeholder jelas, tombol aksi simpan berkilau hijau zamrud.
4. **Tenant Bill Card**: Rincian tagihan lengkap (Nomor Kamar, Periode, Jatuh Tempo, Nominal) + tombol cepat salin nomor rekening + dropzone unggah bukti bayar.
5. **Modal Preview**: Komponen modal tersembunyi yang muncul saat tombol "Lihat bukti" diklik, lengkap dengan tombol tutup `✕`.
