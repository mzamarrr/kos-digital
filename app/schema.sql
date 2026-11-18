-- Skema 6 tabel sesuai makalah Analis (Bagian 3.4 dan Lampiran A)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS pengguna (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,                       -- hash + salt unik, bukan kata sandi asli
    role          TEXT NOT NULL CHECK (role IN ('admin', 'penghuni'))
);

CREATE TABLE IF NOT EXISTS kamar (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nomor     TEXT NOT NULL UNIQUE,                    -- E-03: 409 bila dipakai
    lantai    INTEGER NOT NULL DEFAULT 1,
    kapasitas INTEGER NOT NULL DEFAULT 1,
    fasilitas TEXT NOT NULL DEFAULT '',                -- denormalisasi sadar (teks tunggal) pada v1.0
    tarif     INTEGER NOT NULL CHECK (tarif >= 0)      -- tarif saat ini (rupiah), bukan nominal tagihan lama
    -- status terisi/kosong sengaja TIDAK disimpan: diturunkan dari penghuni aktif
);

CREATE TABLE IF NOT EXISTS penghuni (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    kamar_id       INTEGER NOT NULL REFERENCES kamar(id),
    pengguna_id    INTEGER NOT NULL UNIQUE REFERENCES pengguna(id),
    nama           TEXT NOT NULL,
    no_wa          TEXT NOT NULL,
    tgl_masuk      TEXT NOT NULL,                      -- YYYY-MM-DD
    aktif          INTEGER NOT NULL DEFAULT 1,         -- nonaktif tidak ditagih
    persetujuan_wa INTEGER NOT NULL DEFAULT 0          -- opt-in pesan WhatsApp (R-03)
);

CREATE TABLE IF NOT EXISTS tagihan (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    penghuni_id INTEGER NOT NULL REFERENCES penghuni(id),
    periode     TEXT NOT NULL,                         -- YYYY-MM
    jumlah      INTEGER NOT NULL,                      -- snapshot nominal saat tagihan dibuat
    jatuh_tempo TEXT NOT NULL,                         -- YYYY-MM-DD
    status      TEXT NOT NULL DEFAULT 'Belum dibayar'
                CHECK (status IN ('Belum dibayar', 'Menunggu verifikasi', 'Lunas', 'Ditolak')),
    UNIQUE (penghuni_id, periode)                      -- idempotensi dijaga basis data (NFR-03)
);

CREATE TABLE IF NOT EXISTS pembayaran (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tagihan_id       INTEGER NOT NULL REFERENCES tagihan(id),
    bukti_file       TEXT,                             -- NULL untuk pembayaran tunai yang dicatat admin
    tgl_unggah       TEXT NOT NULL,
    hasil_verifikasi TEXT,                             -- Lunas / Ditolak, diisi admin
    catatan          TEXT,
    verifikator_id   INTEGER REFERENCES pengguna(id),
    tgl_verifikasi   TEXT
);

CREATE TABLE IF NOT EXISTS log_pesan (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tagihan_id  INTEGER NOT NULL REFERENCES tagihan(id),
    jenis       TEXT NOT NULL DEFAULT 'pengingat',
    isi         TEXT NOT NULL,                         -- teks pesan (dipakai jalur manual)
    status_kirim TEXT NOT NULL DEFAULT 'antri' CHECK (status_kirim IN ('antri', 'terkirim', 'gagal')),
    keterangan  TEXT,                                  -- alasan gagal
    waktu       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tagihan_status ON tagihan(status);
CREATE INDEX IF NOT EXISTS idx_log_tagihan ON log_pesan(tagihan_id);
