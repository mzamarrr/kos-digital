# Kontrak API — Kos Digital (E-01 sampai E-10)

Harus sama dengan implementasi di `app/api.py` (dosen dapat mencoba endpoint secara acak).
Semua respons JSON. Autentikasi: header `Authorization: Bearer <token>` (stateless).

Kode kesalahan: **400** data tidak valid · **401** tidak ada/tidak sah token atau login salah · **403** role/kepemilikan tidak berhak · **404** tidak ditemukan · **409** konflik dengan keadaan saat ini.

| ID | Endpoint | Role | Input | Output sukses | Error utama | US |
|----|----------|------|-------|---------------|-------------|----|
| E-01 | `POST /login` | semua | `username`, `password` | `{token, role}` | 400, 401 | US-01 |
| E-02 | `GET /kamar` | admin | – | daftar kamar + `terisi`, `status` | 401, 403 | US-02 |
| E-03 | `POST /kamar` | admin | `nomor`, `lantai`, `kapasitas`, `fasilitas`, `tarif` | 201 data kamar | 400, **409 nomor dipakai** | US-02 |
| E-04 | `POST /penghuni` | admin | `nama`, `no_wa`, `kamar_id`, `tgl_masuk`, `username`, `password` (min 8), `persetujuan_wa` | 201 data penghuni | 400, 404 kamar tidak ada, 409 username dipakai / kamar penuh | US-03 |
| E-05 | `GET /tagihan?periode=&status=` | admin (semua); penghuni (miliknya) | query opsional | daftar tagihan | 400 periode, 401, 403 | US-05, 06 |
| E-06 | `POST /tagihan/generate` | admin (penjadwal memanggil fungsi layanan langsung) | `periode` `YYYY-MM` | `{dibuat, dilewati}` | 400 periode tidak valid | US-04 |
| E-07 | `PATCH /tagihan/{id}/status` | admin | `status` (`Lunas`/`Ditolak`), `catatan` | tagihan terbaru | 400, 404, **409 transisi tidak sah** | US-05, 08 |
| E-08 | `POST /tagihan/{id}/bukti` | penghuni (miliknya) | multipart `file` (jpg/jpeg/png/pdf, maks 2 MB) | 201 `{status: "Menunggu verifikasi"}` | 400 file, **403 bukan miliknya**, 404, 409 status tidak mengizinkan | US-07 |
| E-09 | `GET /laporan/rekap?periode=` | admin | `periode` | `{total, lunas, tunggakan{daftar}}` | 400 periode, 401, 403 | US-09 |
| E-10 | `POST /pengingat/jalankan` | admin (penjadwal memanggil fungsi layanan langsung) | – | `{dibuat, terkirim, gagal, dilewati_tanpa_persetujuan}` | 400 adaptor belum siap, 401, 403 | US-10 |

## Endpoint pendukung (di luar E-01–E-10)
| Endpoint | Role | Fungsi |
|----------|------|--------|
| `PATCH /kamar/{id}` | admin | ubah kamar (field parsial). 400 data tidak valid, 404, **409** nomor dipakai atau kapasitas di bawah penghuni aktif |
| `DELETE /kamar/{id}` | admin | hapus kamar. 404, **409** bila kamar pernah dihuni (riwayat tagihan dijaga) |
| `GET /penghuni` | admin | daftar penghuni |
| `PATCH /penghuni/{id}/nonaktif` | admin | penghuni nonaktif tidak ditagih |
| `GET /tagihan/{id}/bukti` | admin; penghuni (miliknya) | lihat file bukti |
| `GET /pesan` | admin | antrean/log pesan |
| `POST /pesan/{id}/tandai-terkirim` | admin | konfirmasi kirim manual |

## Mesin status tagihan (Tabel 5)
| Dari | Ke | Aktor | Endpoint |
|------|----|-------|----------|
| Belum dibayar | Menunggu verifikasi | Penghuni (miliknya) | E-08 |
| Belum dibayar | Lunas | Admin (bayar tunai) — *asumsi, konfirmasi pengelola* | E-07 |
| Menunggu verifikasi | Lunas / Ditolak | Admin | E-07 |
| Ditolak | Menunggu verifikasi | Penghuni (unggah ulang) — *asumsi* | E-08 |
| Lunas | (tidak ada) | – | **409** bila dicoba |

## Matriks hak akses (Tabel 8)
| Aksi | Admin | Penghuni |
|------|-------|----------|
| Kelola kamar (tambah, ubah, hapus) dan penghuni | Ya | Tidak |
| Lihat tagihan | Semua | Miliknya |
| Buat tagihan periode | Ya | Tidak |
| Ubah status / verifikasi | Ya | Tidak |
| Unggah bukti | Tidak | Miliknya |
| Rekapitulasi | Ya | Tidak |
| Jalankan pengingat | Ya | Tidak |

## Perbedaan yang disengaja dari draf PM (hasil analisis, Tabel 7)
- **E-04** menerima `username` dan `password` karena `penghuni.pengguna_id` membutuhkan akun login.
- **E-06/E-10**: penjadwal tidak lewat HTTP; ia memanggil fungsi layanan yang sama (tanpa kredensial layanan).
- **E-08** memvalidasi tipe dan ukuran file (batas awal: jpg/jpeg/png/pdf, 2 MB; dapat diubah di `config.py`).
- Tabel `log_pesan` ditambah kolom `isi` dan `keterangan` agar jalur manual dan alasan gagal terlihat.
