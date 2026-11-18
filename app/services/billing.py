"""Aturan tagihan di SATU tempat. Dipanggil oleh endpoint E-06 maupun penjadwal (makalah 3.3, 3.6)."""
import calendar
import datetime as dt
import re

PERIODE_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

BELUM, MENUNGGU, LUNAS, DITOLAK = "Belum dibayar", "Menunggu verifikasi", "Lunas", "Ditolak"

# Mesin status (Tabel 5): (dari, ke) -> aktor yang berhak
TRANSISI = {
    (BELUM, MENUNGGU): "penghuni",   # E-08
    (BELUM, LUNAS): "admin",         # E-07 (bayar tunai) -- asumsi, perlu konfirmasi pengelola
    (MENUNGGU, LUNAS): "admin",      # E-07
    (MENUNGGU, DITOLAK): "admin",    # E-07
    (DITOLAK, MENUNGGU): "penghuni", # E-08 (unggah ulang)
}


class BillingError(Exception):
    def __init__(self, message, code=400):
        super().__init__(message)
        self.code = code


def valid_periode(periode):
    return isinstance(periode, str) and bool(PERIODE_RE.match(periode))


def _bounds(periode):
    y, m = int(periode[:4]), int(periode[5:])
    last = calendar.monthrange(y, m)[1]
    return y, m, last


def hitung_jatuh_tempo(periode, tgl_masuk, cfg):
    y, m, last = _bounds(periode)
    if cfg["BILLING_CYCLE"] == "per_penghuni":
        day = min(int(tgl_masuk[8:10]), last)       # tanggal 29-31 dijepit ke akhir bulan (TC-08)
    else:
        day = min(cfg["DUE_DAY"], last)
    return dt.date(y, m, day).isoformat()


def hitung_jumlah(periode, tgl_masuk, tarif, cfg):
    y, m, last = _bounds(periode)
    if cfg["PRORATA"] and tgl_masuk[:7] == periode:
        sisa = last - int(tgl_masuk[8:10]) + 1
        return round(tarif * sisa / last)
    return tarif


def generate_tagihan(db, periode, cfg):
    """Idempoten: UNIQUE(penghuni_id, periode) di basis data menolak baris ganda."""
    if not valid_periode(periode):
        raise BillingError("periode tidak valid, gunakan format YYYY-MM")
    _, _, last = _bounds(periode)
    akhir = f"{periode}-{last:02d}"
    rows = db.execute(
        "SELECT p.id, p.tgl_masuk, k.tarif FROM penghuni p JOIN kamar k ON k.id = p.kamar_id "
        "WHERE p.aktif = 1 AND p.tgl_masuk <= ?", (akhir,)).fetchall()
    dibuat = dilewati = 0
    with db:
        for r in rows:
            cur = db.execute(
                "INSERT OR IGNORE INTO tagihan (penghuni_id, periode, jumlah, jatuh_tempo, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (r["id"], periode, hitung_jumlah(periode, r["tgl_masuk"], r["tarif"], cfg),
                 hitung_jatuh_tempo(periode, r["tgl_masuk"], cfg), BELUM))
            if cur.rowcount:
                dibuat += 1
            else:
                dilewati += 1
    return {"dibuat": dibuat, "dilewati": dilewati}


def ubah_status_admin(db, tagihan_id, status_baru, catatan, admin_id, now=None):
    now = now or dt.datetime.now().isoformat(timespec="seconds")
    if status_baru not in (LUNAS, DITOLAK):
        raise BillingError("status harus 'Lunas' atau 'Ditolak'")
    t = db.execute("SELECT * FROM tagihan WHERE id = ?", (tagihan_id,)).fetchone()
    if not t:
        raise BillingError("tagihan tidak ditemukan", 404)
    if TRANSISI.get((t["status"], status_baru)) != "admin":
        raise BillingError(f"transisi '{t['status']}' -> '{status_baru}' tidak sah", 409)
    with db:
        db.execute("UPDATE tagihan SET status = ? WHERE id = ? AND status = ?",
                   (status_baru, tagihan_id, t["status"]))
        pay = db.execute("SELECT id FROM pembayaran WHERE tagihan_id = ? AND hasil_verifikasi IS NULL "
                         "ORDER BY id DESC LIMIT 1", (tagihan_id,)).fetchone()
        if pay:
            db.execute("UPDATE pembayaran SET hasil_verifikasi=?, catatan=?, verifikator_id=?, tgl_verifikasi=? "
                       "WHERE id = ?", (status_baru, catatan, admin_id, now, pay["id"]))
        else:  # pembayaran tunai: catat jejak audit tanpa file
            db.execute("INSERT INTO pembayaran (tagihan_id, bukti_file, tgl_unggah, hasil_verifikasi, catatan, "
                       "verifikator_id, tgl_verifikasi) VALUES (?, NULL, ?, ?, ?, ?, ?)",
                       (tagihan_id, now, status_baru, catatan, admin_id, now))
    return db.execute("SELECT * FROM tagihan WHERE id = ?", (tagihan_id,)).fetchone()


def rekap(db, periode):
    if not valid_periode(periode):
        raise BillingError("periode tidak valid, gunakan format YYYY-MM")
    rows = db.execute(
        "SELECT t.id, t.status, t.jumlah, t.jatuh_tempo, p.nama, k.nomor AS kamar FROM tagihan t "
        "JOIN penghuni p ON p.id = t.penghuni_id JOIN kamar k ON k.id = p.kamar_id "
        "WHERE t.periode = ? ORDER BY k.nomor", (periode,)).fetchall()
    lunas = [r for r in rows if r["status"] == LUNAS]
    tunggakan = [r for r in rows if r["status"] != LUNAS]
    return {
        "periode": periode,
        "total": {"jumlah_tagihan": len(rows), "nominal": sum(r["jumlah"] for r in rows)},
        "lunas": {"jumlah_tagihan": len(lunas), "nominal": sum(r["jumlah"] for r in lunas)},
        "tunggakan": {"jumlah_tagihan": len(tunggakan), "nominal": sum(r["jumlah"] for r in tunggakan),
                      "daftar": [{"tagihan_id": r["id"], "nama": r["nama"], "kamar": r["kamar"],
                                  "status": r["status"], "jumlah": r["jumlah"],
                                  "jatuh_tempo": r["jatuh_tempo"]} for r in tunggakan]},
    }
