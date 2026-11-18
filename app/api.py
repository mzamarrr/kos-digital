"""Endpoint REST E-01 sampai E-10 (kontrak: docs/kontrak-api.md).
Tolak-bawaan: setiap rute wajib menyebut role yang berhak; kepemilikan dicek di setiap permintaan."""
import datetime as dt
import functools
import os
import sqlite3
import uuid

import jwt
from flask import Blueprint, current_app, g, jsonify, request, send_file

from . import security
from .db import connect
from .services import billing, reminders, wa

bp = Blueprint("api", __name__)


def cfg():
    return current_app.config


def db():
    if "db" not in g:
        g.db = connect(cfg()["DB_PATH"])
    return g.db


@bp.teardown_app_request
def close_db(_exc):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def err(message, code):
    return jsonify(error=message), code


def auth(*roles):
    """401 bila token tidak ada/tidak sah; 403 bila role tidak berhak."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                return err("token tidak ada", 401)
            try:
                payload = security.read_token(header[7:], cfg()["SECRET_KEY"])
            except jwt.PyJWTError:
                return err("token tidak sah atau kedaluwarsa", 401)
            user = db().execute("SELECT id, role FROM pengguna WHERE id = ?", (payload["sub"],)).fetchone()
            if not user:
                return err("pengguna tidak ditemukan", 401)
            if user["role"] not in roles:
                return err("tidak berhak mengakses", 403)
            g.user = user
            return fn(*a, **kw)
        return wrapper
    return deco


def my_penghuni_id():
    row = db().execute("SELECT id FROM penghuni WHERE pengguna_id = ?", (g.user["id"],)).fetchone()
    return row["id"] if row else None


def body():
    return request.get_json(silent=True) or {}


def tagihan_dict(r):
    return {k: r[k] for k in ("id", "penghuni_id", "periode", "jumlah", "jatuh_tempo", "status")}


# ---------- E-01 ----------
@bp.post("/login")
def login():
    d = body()
    u, p = d.get("username"), d.get("password")
    if not isinstance(u, str) or not isinstance(p, str) or not u or not p:
        return err("username dan password wajib diisi", 400)
    row = db().execute("SELECT * FROM pengguna WHERE username = ?", (u,)).fetchone()
    if not row or not security.verify_password(p, row["password_hash"]):
        return err("username atau password salah", 401)
    token = security.make_token(row["id"], row["role"], cfg()["SECRET_KEY"], cfg()["TOKEN_TTL_HOURS"])
    return jsonify(token=token, role=row["role"])


# ---------- E-02, E-03 ----------
@bp.get("/kamar")
@auth("admin")
def list_kamar():
    rows = db().execute(
        "SELECT k.*, (SELECT COUNT(*) FROM penghuni p WHERE p.kamar_id = k.id AND p.aktif = 1) AS terisi "
        "FROM kamar k ORDER BY k.nomor").fetchall()
    return jsonify([{**{k: r[k] for k in ("id", "nomor", "lantai", "kapasitas", "fasilitas", "tarif")},
                     "terisi": r["terisi"], "status": "terisi" if r["terisi"] else "kosong"} for r in rows])


@bp.post("/kamar")
@auth("admin")
def add_kamar():
    d = body()
    nomor = str(d.get("nomor", "")).strip()
    tarif, lantai, kapasitas = d.get("tarif"), d.get("lantai", 1), d.get("kapasitas", 1)
    if not nomor or not all(isinstance(x, int) and not isinstance(x, bool) for x in (tarif, lantai, kapasitas)) \
            or tarif < 0 or kapasitas < 1:
        return err("data kamar tidak valid (nomor, tarif, lantai, kapasitas)", 400)
    try:
        with db():
            cur = db().execute("INSERT INTO kamar (nomor, lantai, kapasitas, fasilitas, tarif) VALUES (?,?,?,?,?)",
                               (nomor, lantai, kapasitas, str(d.get("fasilitas", "")), tarif))
    except sqlite3.IntegrityError:
        return err("nomor kamar sudah dipakai", 409)
    row = db().execute("SELECT * FROM kamar WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify({k: row[k] for k in ("id", "nomor", "lantai", "kapasitas", "fasilitas", "tarif")}), 201


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


@bp.patch("/kamar/<int:kid>")
@auth("admin")
def edit_kamar(kid):
    k = db().execute("SELECT * FROM kamar WHERE id = ?", (kid,)).fetchone()
    if not k:
        return err("kamar tidak ditemukan", 404)
    d = body()
    if not d or not set(d) <= {"nomor", "lantai", "kapasitas", "fasilitas", "tarif"}:
        return err("kirim minimal satu field: nomor, lantai, kapasitas, fasilitas, tarif", 400)
    nomor = str(d.get("nomor", k["nomor"])).strip()
    lantai, kapasitas, tarif = d.get("lantai", k["lantai"]), d.get("kapasitas", k["kapasitas"]), d.get("tarif", k["tarif"])
    fasilitas = str(d.get("fasilitas", k["fasilitas"]))
    if not nomor or not all(_is_int(v) for v in (lantai, kapasitas, tarif)) or tarif < 0 or kapasitas < 1:
        return err("data kamar tidak valid", 400)
    terisi = db().execute("SELECT COUNT(*) c FROM penghuni WHERE kamar_id = ? AND aktif = 1", (kid,)).fetchone()["c"]
    if kapasitas < terisi:
        return err(f"kapasitas tidak boleh di bawah jumlah penghuni aktif ({terisi})", 409)
    try:
        with db():
            db().execute("UPDATE kamar SET nomor=?, lantai=?, kapasitas=?, fasilitas=?, tarif=? WHERE id=?",
                         (nomor, lantai, kapasitas, fasilitas, tarif, kid))
    except sqlite3.IntegrityError:
        return err("nomor kamar sudah dipakai", 409)
    return jsonify(id=kid, nomor=nomor, lantai=lantai, kapasitas=kapasitas, fasilitas=fasilitas, tarif=tarif)


@bp.delete("/kamar/<int:kid>")
@auth("admin")
def hapus_kamar(kid):
    if not db().execute("SELECT 1 FROM kamar WHERE id = ?", (kid,)).fetchone():
        return err("kamar tidak ditemukan", 404)
    # kamar yang pernah dihuni (aktif maupun nonaktif) tidak dihapus agar riwayat tagihan tetap utuh
    if db().execute("SELECT 1 FROM penghuni WHERE kamar_id = ? LIMIT 1", (kid,)).fetchone():
        return err("kamar memiliki penghuni atau riwayat penghuni, tidak dapat dihapus", 409)
    with db():
        db().execute("DELETE FROM kamar WHERE id = ?", (kid,))
    return jsonify(id=kid, dihapus=True)


# ---------- E-04 ----------
@bp.post("/penghuni")
@auth("admin")
def add_penghuni():
    d = body()
    nama, no_wa = str(d.get("nama", "")).strip(), str(d.get("no_wa", "")).strip()
    username, password = str(d.get("username", "")).strip(), d.get("password")
    try:
        tgl = dt.date.fromisoformat(str(d.get("tgl_masuk", ""))).isoformat()
    except ValueError:
        return err("tgl_masuk harus berformat YYYY-MM-DD", 400)
    if not (nama and no_wa.isdigit() and username and isinstance(password, str) and len(password) >= 8):
        return err("data tidak valid (nama, no_wa angka, username, password minimal 8 karakter)", 400)
    kamar_id = d.get("kamar_id")
    kamar = db().execute("SELECT id, kapasitas FROM kamar WHERE id = ?", (kamar_id,)).fetchone() \
        if isinstance(kamar_id, int) else None
    if not kamar:
        return err("kamar tidak ada", 404)
    terisi = db().execute("SELECT COUNT(*) c FROM penghuni WHERE kamar_id = ? AND aktif = 1", (kamar["id"],)).fetchone()["c"]
    if terisi >= kamar["kapasitas"]:
        return err("kamar sudah penuh", 409)
    try:
        with db():
            u = db().execute("INSERT INTO pengguna (username, password_hash, role) VALUES (?, ?, 'penghuni')",
                             (username, security.hash_password(password, n=cfg()["SCRYPT_N"])))
            cur = db().execute(
                "INSERT INTO penghuni (kamar_id, pengguna_id, nama, no_wa, tgl_masuk, aktif, persetujuan_wa) "
                "VALUES (?,?,?,?,?,1,?)", (kamar["id"], u.lastrowid, nama, no_wa, tgl, 1 if d.get("persetujuan_wa") else 0))
    except sqlite3.IntegrityError:
        return err("username sudah dipakai", 409)
    return jsonify(id=cur.lastrowid, nama=nama, no_wa=no_wa, kamar_id=kamar["id"], tgl_masuk=tgl,
                   username=username, aktif=True), 201


@bp.get("/penghuni")
@auth("admin")
def list_penghuni():
    rows = db().execute("SELECT p.*, k.nomor AS kamar, u.username FROM penghuni p JOIN kamar k ON k.id = p.kamar_id "
                        "JOIN pengguna u ON u.id = p.pengguna_id ORDER BY k.nomor, p.nama").fetchall()
    return jsonify([{"id": r["id"], "nama": r["nama"], "no_wa": r["no_wa"], "kamar": r["kamar"],
                     "kamar_id": r["kamar_id"], "tgl_masuk": r["tgl_masuk"], "aktif": bool(r["aktif"]),
                     "persetujuan_wa": bool(r["persetujuan_wa"]), "username": r["username"]} for r in rows])


@bp.patch("/penghuni/<int:pid>/nonaktif")
@auth("admin")
def nonaktifkan(pid):
    with db():
        cur = db().execute("UPDATE penghuni SET aktif = 0 WHERE id = ?", (pid,))
    return (jsonify(id=pid, aktif=False), 200) if cur.rowcount else err("penghuni tidak ditemukan", 404)


# ---------- E-05 ----------
@bp.get("/tagihan")
@auth("admin", "penghuni")
def list_tagihan():
    sql = ("SELECT t.*, p.nama, k.nomor AS kamar FROM tagihan t JOIN penghuni p ON p.id = t.penghuni_id "
           "JOIN kamar k ON k.id = p.kamar_id WHERE 1=1")
    args = []
    if g.user["role"] == "penghuni":  # hanya miliknya
        sql += " AND t.penghuni_id = ?"
        args.append(my_penghuni_id() or -1)
    periode, status = request.args.get("periode"), request.args.get("status")
    if periode:
        if not billing.valid_periode(periode):
            return err("periode tidak valid", 400)
        sql += " AND t.periode = ?"
        args.append(periode)
    if status:
        sql += " AND t.status = ?"
        args.append(status)
    rows = db().execute(sql + " ORDER BY t.periode DESC, k.nomor", args).fetchall()
    return jsonify([{**tagihan_dict(r), "nama": r["nama"], "kamar": r["kamar"]} for r in rows])


# ---------- E-06 ----------
@bp.post("/tagihan/generate")
@auth("admin")
def generate():
    try:
        return jsonify(billing.generate_tagihan(db(), body().get("periode"), cfg()))
    except billing.BillingError as e:
        return err(str(e), e.code)


# ---------- E-07 ----------
@bp.patch("/tagihan/<int:tid>/status")
@auth("admin")
def ubah_status(tid):
    d = body()
    try:
        t = billing.ubah_status_admin(db(), tid, d.get("status"), d.get("catatan"), g.user["id"])
    except billing.BillingError as e:
        return err(str(e), e.code)
    return jsonify(tagihan_dict(t))


# ---------- E-08 ----------
@bp.post("/tagihan/<int:tid>/bukti")
@auth("penghuni")
def unggah_bukti(tid):
    t = db().execute("SELECT * FROM tagihan WHERE id = ?", (tid,)).fetchone()
    if not t:
        return err("tagihan tidak ditemukan", 404)
    if t["penghuni_id"] != my_penghuni_id():
        return err("bukan tagihan Anda", 403)
    f = request.files.get("file")
    if not f or not f.filename:
        return err("file wajib diisi", 400)
    ext = f.filename.rsplit(".", 1)[-1].lower() if "." in f.filename else ""
    if ext not in cfg()["ALLOWED_EXT"]:
        return err("tipe file harus jpg, jpeg, png, atau pdf", 400)
    data = f.read(cfg()["MAX_UPLOAD_BYTES"] + 1)
    if len(data) > cfg()["MAX_UPLOAD_BYTES"] or not data:
        return err("ukuran file kosong atau melebihi batas", 400)
    if billing.TRANSISI.get((t["status"], billing.MENUNGGU)) != "penghuni":
        return err(f"tagihan berstatus '{t['status']}' tidak dapat diunggah buktinya", 409)
    name = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(cfg()["UPLOAD_DIR"], name), "wb") as out:
        out.write(data)
    now = dt.datetime.now().isoformat(timespec="seconds")
    with db():
        db().execute("UPDATE tagihan SET status = ? WHERE id = ?", (billing.MENUNGGU, tid))
        cur = db().execute("INSERT INTO pembayaran (tagihan_id, bukti_file, tgl_unggah) VALUES (?,?,?)",
                           (tid, name, now))
    return jsonify(id=cur.lastrowid, tagihan_id=tid, status=billing.MENUNGGU, tgl_unggah=now), 201


@bp.get("/tagihan/<int:tid>/bukti")
@auth("admin", "penghuni")
def lihat_bukti(tid):
    t = db().execute("SELECT * FROM tagihan WHERE id = ?", (tid,)).fetchone()
    if not t:
        return err("tagihan tidak ditemukan", 404)
    if g.user["role"] == "penghuni" and t["penghuni_id"] != my_penghuni_id():
        return err("bukan tagihan Anda", 403)
    p = db().execute("SELECT bukti_file FROM pembayaran WHERE tagihan_id = ? AND bukti_file IS NOT NULL "
                     "ORDER BY id DESC LIMIT 1", (tid,)).fetchone()
    if not p:
        return err("belum ada bukti", 404)
    return send_file(os.path.join(cfg()["UPLOAD_DIR"], p["bukti_file"]))


# ---------- E-09 ----------
@bp.get("/laporan/rekap")
@auth("admin")
def laporan():
    try:
        return jsonify(billing.rekap(db(), request.args.get("periode")))
    except billing.BillingError as e:
        return err(str(e), e.code)


# ---------- E-10 ----------
@bp.post("/pengingat/jalankan")
@auth("admin")
def pengingat():
    try:
        adapter = wa.get_adapter(cfg()["WA_ADAPTER"])
    except wa.WAError as e:  # adaptor belum siap -> tagihan tetap aman, hanya pengingat yang gagal
        return err(f"adaptor pengiriman belum siap: {e}", 400)
    return jsonify(reminders.jalankan_pengingat(db(), cfg(), adapter))


# ---------- Pendukung jalur manual ----------
@bp.get("/pesan")
@auth("admin")
def list_pesan():
    rows = db().execute(
        "SELECT l.*, p.nama, p.no_wa FROM log_pesan l JOIN tagihan t ON t.id = l.tagihan_id "
        "JOIN penghuni p ON p.id = t.penghuni_id ORDER BY l.id DESC LIMIT 100").fetchall()
    return jsonify([{"id": r["id"], "tagihan_id": r["tagihan_id"], "nama": r["nama"], "no_wa": r["no_wa"],
                     "isi": r["isi"], "status_kirim": r["status_kirim"], "keterangan": r["keterangan"],
                     "waktu": r["waktu"]} for r in rows])


@bp.post("/pesan/<int:mid>/tandai-terkirim")
@auth("admin")
def tandai_terkirim(mid):
    with db():
        cur = db().execute("UPDATE log_pesan SET status_kirim = 'terkirim', keterangan = 'dikirim manual oleh admin' "
                           "WHERE id = ? AND status_kirim = 'antri'", (mid,))
    return jsonify(id=mid, status_kirim="terkirim") if cur.rowcount else err("pesan tidak ada atau bukan antrean", 404)
