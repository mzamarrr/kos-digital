"""Job pengingat (E-10). Terpisah dari pembuatan tagihan: kegagalan kirim tidak menghalangi tagihan (3.6)."""
import datetime as dt

from .billing import BELUM, DITOLAK
from .wa import WAError


def _rupiah(n):
    return "Rp" + f"{n:,}".replace(",", ".")


def susun_pesan(nama, periode, jumlah, jatuh_tempo):
    return (f"Halo {nama}, pengingat tagihan kos periode {periode} sebesar {_rupiah(jumlah)} "
            f"(jatuh tempo {jatuh_tempo}). Mohon unggah bukti pembayaran di aplikasi. Terima kasih.")


def jalankan_pengingat(db, cfg, adapter, today=None):
    today = today or dt.date.today()
    batas = (today + dt.timedelta(days=cfg["REMINDER_DAYS_BEFORE"])).isoformat()
    # tanggal log mengikuti tanggal job agar pengecekan "sudah diingatkan hari ini" konsisten
    now = f"{today.isoformat()}T{dt.datetime.now().strftime('%H:%M:%S')}"
    # 'Menunggu verifikasi' dan 'Lunas' dikecualikan (R-07, TC-11)
    rows = db.execute(
        "SELECT t.id, t.periode, t.jumlah, t.jatuh_tempo, p.nama, p.no_wa, p.persetujuan_wa "
        "FROM tagihan t JOIN penghuni p ON p.id = t.penghuni_id "
        "WHERE t.status IN (?, ?) AND p.aktif = 1 AND t.jatuh_tempo <= ? "
        "AND NOT EXISTS (SELECT 1 FROM log_pesan l WHERE l.tagihan_id = t.id AND l.jenis = 'pengingat' "
        "AND substr(l.waktu, 1, 10) = ?)",
        (BELUM, DITOLAK, batas, today.isoformat())).fetchall()
    hasil = {"dibuat": 0, "terkirim": 0, "gagal": 0, "dilewati_tanpa_persetujuan": 0}
    for r in rows:
        if adapter.butuh_opt_in and not r["persetujuan_wa"]:
            hasil["dilewati_tanpa_persetujuan"] += 1
            continue
        teks = susun_pesan(r["nama"], r["periode"], r["jumlah"], r["jatuh_tempo"])
        with db:  # dicatat dulu sebagai antrean, sebelum adaptor mengirim
            cur = db.execute("INSERT INTO log_pesan (tagihan_id, jenis, isi, status_kirim, waktu) "
                             "VALUES (?, 'pengingat', ?, 'antri', ?)", (r["id"], teks, now))
        log_id = cur.lastrowid
        hasil["dibuat"] += 1
        try:
            status = adapter.kirim(r["no_wa"], teks)
            keterangan = None
        except WAError as e:
            status, keterangan = "gagal", str(e)
        if status != "antri":
            with db:
                db.execute("UPDATE log_pesan SET status_kirim = ?, keterangan = ? WHERE id = ?",
                           (status, keterangan, log_id))
        if status == "terkirim":
            hasil["terkirim"] += 1
        elif status == "gagal":
            hasil["gagal"] += 1
    return hasil
