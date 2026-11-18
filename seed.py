"""Data contoh FIKTIF untuk pengembangan dan demo. Jangan dipakai di produksi.
  python seed.py            -> akun: admin / admin12345, penghuni: budi / budi12345, sari / sari12345
"""
import datetime as dt
import os

from app.config import Config
from app.db import connect, init_db
from app.security import hash_password

ADMIN_PW = os.environ.get("KOS_ADMIN_PW", "admin12345")


def main():
    init_db(Config.DB_PATH)
    db = connect(Config.DB_PATH)
    if db.execute("SELECT COUNT(*) c FROM pengguna").fetchone()["c"]:
        print("Basis data sudah berisi; seed dilewati.")
        return
    h = lambda pw: hash_password(pw, n=Config.SCRYPT_N)
    with db:
        db.execute("INSERT INTO pengguna (username, password_hash, role) VALUES ('admin', ?, 'admin')", (h(ADMIN_PW),))
        for nomor, lantai, fas, tarif in [("A1", 1, "Kasur, lemari, kamar mandi dalam", 900000),
                                         ("A2", 1, "Kasur, lemari", 700000),
                                         ("B1", 2, "Kasur, lemari, AC, kamar mandi dalam", 1200000),
                                         ("B2", 2, "Kasur, lemari, AC", 1100000)]:
            db.execute("INSERT INTO kamar (nomor, lantai, kapasitas, fasilitas, tarif) VALUES (?,1,1,?,?)",
                       (nomor, fas, tarif))
            db.execute("UPDATE kamar SET lantai = ? WHERE nomor = ?", (lantai, nomor))
        today = dt.date.today()
        for username, pw, nama, wa, kamar, masuk in [("budi", "budi12345", "Budi Santoso", "628111000001", 1,
                                                       today.replace(day=1) - dt.timedelta(days=60)),
                                                      ("sari", "sari12345", "Sari Lestari", "628111000002", 3,
                                                       today.replace(day=1) - dt.timedelta(days=20)),
                                                      ("kresna", "kresna12345", "Kresna", "6281281120360", 2,
                                                       today.replace(day=1) - dt.timedelta(days=15)),
                                                      ("torik", "torik12345", "Torik", "6281511613869", 4,
                                                       today.replace(day=1) - dt.timedelta(days=10))]:
            u = db.execute("INSERT INTO pengguna (username, password_hash, role) VALUES (?,?, 'penghuni')",
                           (username, h(pw)))
            db.execute("INSERT INTO penghuni (kamar_id, pengguna_id, nama, no_wa, tgl_masuk, aktif, persetujuan_wa) "
                       "VALUES (?,?,?,?,?,1,1)", (kamar, u.lastrowid, nama, wa, masuk.isoformat()))
    print("Seed selesai (data fiktif). Login: admin/admin12345, budi/budi12345, sari/sari12345, kresna/kresna12345, torik/torik12345")


if __name__ == "__main__":
    main()
