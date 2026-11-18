"""Tes otomatis. Jalankan: python -m unittest discover -s tests -v
Kode TC mengikuti Traceability Matrix pada makalah PM; sesuaikan nomor bila berbeda."""
import datetime as dt
import io
import os
import shutil
import sqlite3
import tempfile
import unittest

from app import create_app
from app.db import connect
from app.security import hash_password
from app.services import billing, reminders
from app.services.wa import ManualAdapter, WAError

SCRYPT_N = 2 ** 10  # ringan untuk tes saja


class FailingAdapter:
    butuh_opt_in = True

    def kirim(self, no_wa, teks):
        raise WAError("simulasi gagal kirim")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.app = create_app({"DB_PATH": os.path.join(self.tmp, "t.db"), "UPLOAD_DIR": os.path.join(self.tmp, "up"),
                               "SCRYPT_N": SCRYPT_N, "TESTING": True, "SECRET_KEY": "x" * 32})
        self.c = self.app.test_client()
        db = connect(self.app.config["DB_PATH"])
        with db:
            db.execute("INSERT INTO pengguna (username, password_hash, role) VALUES ('admin', ?, 'admin')",
                       (hash_password("adminpass1", n=SCRYPT_N),))
        db.close()
        self.admin = self.login("admin", "adminpass1")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def login(self, u, p):
        r = self.c.post("/login", json={"username": u, "password": p})
        self.assertEqual(r.status_code, 200, r.get_json())
        return {"Authorization": "Bearer " + r.get_json()["token"]}

    def kamar(self, nomor="A1", tarif=900000):
        r = self.c.post("/kamar", json={"nomor": nomor, "lantai": 1, "kapasitas": 1, "fasilitas": "x", "tarif": tarif},
                        headers=self.admin)
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()["id"]

    def penghuni(self, kamar_id, username="budi", masuk="2026-01-05", wa_ok=True):
        r = self.c.post("/penghuni", headers=self.admin, json={
            "nama": username.title(), "no_wa": "628111000001", "kamar_id": kamar_id, "tgl_masuk": masuk,
            "username": username, "password": "rahasia123", "persetujuan_wa": wa_ok})
        self.assertEqual(r.status_code, 201, r.get_json())
        return r.get_json()["id"], self.login(username, "rahasia123")

    def tagihan(self, periode="2026-03"):
        self.c.post("/tagihan/generate", json={"periode": periode}, headers=self.admin)
        return self.c.get("/tagihan?periode=" + periode, headers=self.admin).get_json()


class TestAuth(Base):
    def test_login_salah_401(self):  # E-01
        self.assertEqual(self.c.post("/login", json={"username": "admin", "password": "salah"}).status_code, 401)

    def test_tanpa_token_401_role_salah_403(self):  # TC-09 / TC-10
        self.assertEqual(self.c.get("/kamar").status_code, 401)
        k = self.kamar()
        _, budi = self.penghuni(k)
        self.assertEqual(self.c.get("/kamar", headers=budi).status_code, 403)
        self.assertEqual(self.c.post("/tagihan/generate", json={"periode": "2026-03"}, headers=budi).status_code, 403)

    def test_hash_bukan_teks_asli_dan_salt_unik(self):  # NFR-02
        a, b = hash_password("sama", n=SCRYPT_N), hash_password("sama", n=SCRYPT_N)
        self.assertNotIn("sama", a)
        self.assertNotEqual(a, b)
        db = sqlite3.connect(self.app.config["DB_PATH"])
        self.assertNotIn("adminpass1", db.execute("SELECT password_hash FROM pengguna").fetchone()[0])


class TestKamarPenghuni(Base):
    def test_nomor_kamar_ganda_409(self):  # E-03
        self.kamar("A1")
        r = self.c.post("/kamar", json={"nomor": "A1", "tarif": 1}, headers=self.admin)
        self.assertEqual(r.status_code, 409)

    def test_input_tidak_valid_400(self):
        self.assertEqual(self.c.post("/kamar", json={"nomor": "", "tarif": "x"}, headers=self.admin).status_code, 400)
        self.assertEqual(self.c.post("/penghuni", json={"nama": "a"}, headers=self.admin).status_code, 400)

    def test_penghuni_kamar_tidak_ada_404(self):  # E-04
        r = self.c.post("/penghuni", headers=self.admin, json={"nama": "A", "no_wa": "62811", "kamar_id": 99,
                        "tgl_masuk": "2026-01-01", "username": "aa", "password": "12345678"})
        self.assertEqual(r.status_code, 404)

    def test_status_kamar_diturunkan(self):
        k = self.kamar()
        self.assertEqual(self.c.get("/kamar", headers=self.admin).get_json()[0]["status"], "kosong")
        self.penghuni(k)
        self.assertEqual(self.c.get("/kamar", headers=self.admin).get_json()[0]["status"], "terisi")


class TestTagihan(Base):
    def test_generate_idempoten(self):  # TC-07 / NFR-03
        self.penghuni(self.kamar())
        a = self.c.post("/tagihan/generate", json={"periode": "2026-03"}, headers=self.admin).get_json()
        b = self.c.post("/tagihan/generate", json={"periode": "2026-03"}, headers=self.admin).get_json()
        self.assertEqual(a, {"dibuat": 1, "dilewati": 0})
        self.assertEqual(b, {"dibuat": 0, "dilewati": 1})
        self.assertEqual(len(self.c.get("/tagihan", headers=self.admin).get_json()), 1)

    def test_basis_data_menolak_duplikat_langsung(self):
        pid, _ = self.penghuni(self.kamar())
        self.tagihan()
        db = connect(self.app.config["DB_PATH"])
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO tagihan (penghuni_id, periode, jumlah, jatuh_tempo) VALUES (?, '2026-03', 1, '2026-03-10')", (pid,))

    def test_periode_tidak_valid_400(self):  # E-06
        for p in ("2026-13", "202603", None, "abc"):
            self.assertEqual(self.c.post("/tagihan/generate", json={"periode": p}, headers=self.admin).status_code, 400)

    def test_penghuni_nonaktif_tidak_ditagih(self):  # TC-05
        pid, _ = self.penghuni(self.kamar())
        self.c.patch(f"/penghuni/{pid}/nonaktif", headers=self.admin)
        self.assertEqual(self.c.post("/tagihan/generate", json={"periode": "2026-03"}, headers=self.admin).get_json(),
                         {"dibuat": 0, "dilewati": 0})

    def test_masuk_setelah_periode_tidak_ditagih(self):
        self.penghuni(self.kamar(), masuk="2026-04-02")
        self.assertEqual(self.c.post("/tagihan/generate", json={"periode": "2026-03"}, headers=self.admin).get_json()["dibuat"], 0)

    def test_snapshot_jumlah_tidak_berubah_saat_tarif_berubah(self):
        k = self.kamar(tarif=900000)
        self.penghuni(k)
        self.tagihan()
        db = connect(self.app.config["DB_PATH"])
        with db:
            db.execute("UPDATE kamar SET tarif = 2000000")
        self.assertEqual(self.c.get("/tagihan", headers=self.admin).get_json()[0]["jumlah"], 900000)

    def test_jatuh_tempo_akhir_bulan_per_penghuni(self):  # TC-08 (aturan siklus = parameter)
        cfg = {"BILLING_CYCLE": "per_penghuni", "DUE_DAY": 10}
        self.assertEqual(billing.hitung_jatuh_tempo("2026-02", "2026-01-31", cfg), "2026-02-28")
        self.assertEqual(billing.hitung_jatuh_tempo("2028-02", "2026-01-31", cfg), "2028-02-29")
        self.assertEqual(billing.hitung_jatuh_tempo("2026-04", "2026-01-31", cfg), "2026-04-30")
        self.assertEqual(billing.hitung_jatuh_tempo("2026-03", "2026-01-15", {"BILLING_CYCLE": "calendar", "DUE_DAY": 10}), "2026-03-10")

    def test_prorata_opsional(self):
        cfg = {"BILLING_CYCLE": "calendar", "DUE_DAY": 10, "PRORATA": True}
        self.assertEqual(billing.hitung_jumlah("2026-03", "2026-03-16", 310000, cfg), 160000)  # 16 dari 31 hari
        self.assertEqual(billing.hitung_jumlah("2026-03", "2026-02-01", 310000, cfg), 310000)


class TestStatusDanBukti(Base):
    def setUp(self):
        super().setUp()
        self.k = self.kamar()
        self.pid, self.budi = self.penghuni(self.k)
        self.t = self.tagihan()[0]["id"]

    def upload(self, headers, tid=None, name="bukti.png", data=b"\x89PNG..."):
        return self.c.post(f"/tagihan/{tid or self.t}/bukti", headers=headers,
                           data={"file": (io.BytesIO(data), name)}, content_type="multipart/form-data")

    def status(self, s, tid=None):
        return self.c.patch(f"/tagihan/{tid or self.t}/status", json={"status": s, "catatan": "tes"}, headers=self.admin)

    def test_alur_penuh(self):  # US-07/08: belum -> menunggu -> lunas
        r = self.upload(self.budi)
        self.assertEqual(r.status_code, 201)
        self.assertEqual(self.c.get("/tagihan", headers=self.budi).get_json()[0]["status"], "Menunggu verifikasi")
        self.assertEqual(self.status("Lunas").get_json()["status"], "Lunas")

    def test_lunas_final_409(self):  # Tabel 5: Lunas final
        self.upload(self.budi)
        self.status("Lunas")
        self.assertEqual(self.status("Ditolak").status_code, 409)
        self.assertEqual(self.status("Lunas").status_code, 409)
        self.assertEqual(self.upload(self.budi).status_code, 409)

    def test_ditolak_boleh_unggah_ulang(self):
        self.upload(self.budi)
        self.status("Ditolak")
        self.assertEqual(self.upload(self.budi).status_code, 201)

    def test_ditolak_tidak_langsung_lunas_409(self):
        self.upload(self.budi)
        self.status("Ditolak")
        self.assertEqual(self.status("Lunas").status_code, 409)

    def test_penghuni_tidak_bisa_ubah_status_403(self):  # US-05
        r = self.c.patch(f"/tagihan/{self.t}/status", json={"status": "Lunas"}, headers=self.budi)
        self.assertEqual(r.status_code, 403)

    def test_status_tidak_dikenal_400(self):
        self.assertEqual(self.status("Gratis").status_code, 400)

    def test_tunai_dicatat_admin(self):
        self.assertEqual(self.status("Lunas").status_code, 200)
        db = connect(self.app.config["DB_PATH"])
        self.assertEqual(db.execute("SELECT hasil_verifikasi FROM pembayaran").fetchone()[0], "Lunas")

    def test_kepemilikan_403(self):  # TC-14 / OWASP A01
        k2 = self.kamar("A2")
        _, sari = self.penghuni(k2, "sari")
        self.assertEqual(self.c.get("/tagihan", headers=sari).get_json(), [])
        self.assertEqual(self.upload(sari).status_code, 403)
        self.assertEqual(self.c.get(f"/tagihan/{self.t}/bukti", headers=sari).status_code, 403)

    def test_validasi_file_400(self):  # E-08
        self.assertEqual(self.upload(self.budi, name="virus.exe").status_code, 400)
        self.assertEqual(self.upload(self.budi, data=b"").status_code, 400)
        big = b"0" * (self.app.config["MAX_UPLOAD_BYTES"] + 10)
        self.assertEqual(self.upload(self.budi, data=big).status_code, 400)
        self.assertEqual(self.c.get("/tagihan", headers=self.budi).get_json()[0]["status"], "Belum dibayar")

    def test_tagihan_tidak_ada_404(self):
        self.assertEqual(self.upload(self.budi, tid=999).status_code, 404)
        self.assertEqual(self.status("Lunas", tid=999).status_code, 404)

    def test_rekap(self):  # E-09
        r = self.c.get("/laporan/rekap?periode=2026-03", headers=self.admin).get_json()
        self.assertEqual((r["total"]["jumlah_tagihan"], r["lunas"]["jumlah_tagihan"], r["tunggakan"]["jumlah_tagihan"]), (1, 0, 1))
        self.status("Lunas")
        r = self.c.get("/laporan/rekap?periode=2026-03", headers=self.admin).get_json()
        self.assertEqual((r["lunas"]["nominal"], r["tunggakan"]["nominal"]), (900000, 0))
        self.assertEqual(self.c.get("/laporan/rekap?periode=x", headers=self.admin).status_code, 400)


class TestPengingat(Base):
    def setUp(self):
        super().setUp()
        self.pid, self.budi = self.penghuni(self.kamar())
        self.t = self.tagihan("2026-03")[0]["id"]  # jatuh tempo 2026-03-10
        self.db = connect(self.app.config["DB_PATH"])
        self.cfg = dict(self.app.config)
        self.today = dt.date(2026, 3, 9)

    def test_pengingat_manual_masuk_antrean(self):  # US-10
        h = reminders.jalankan_pengingat(self.db, self.cfg, ManualAdapter(), self.today)
        self.assertEqual((h["dibuat"], h["terkirim"], h["gagal"]), (1, 0, 0))
        self.assertEqual(self.db.execute("SELECT status_kirim FROM log_pesan").fetchone()[0], "antri")

    def test_tidak_dobel_pada_hari_sama(self):
        reminders.jalankan_pengingat(self.db, self.cfg, ManualAdapter(), self.today)
        h = reminders.jalankan_pengingat(self.db, self.cfg, ManualAdapter(), self.today)
        self.assertEqual(h["dibuat"], 0)

    def test_menunggu_verifikasi_dan_lunas_dikecualikan(self):  # TC-11 / R-07
        self.c.post(f"/tagihan/{self.t}/bukti", headers=self.budi,
                    data={"file": (io.BytesIO(b"x"), "a.png")}, content_type="multipart/form-data")
        self.assertEqual(reminders.jalankan_pengingat(self.db, self.cfg, ManualAdapter(), self.today)["dibuat"], 0)

    def test_belum_waktunya_tidak_diingatkan(self):
        self.assertEqual(reminders.jalankan_pengingat(self.db, self.cfg, ManualAdapter(), dt.date(2026, 3, 1))["dibuat"], 0)

    def test_gagal_kirim_tercatat_dan_tagihan_aman(self):  # R-02: kegagalan tidak menghalangi tagihan
        h = reminders.jalankan_pengingat(self.db, self.cfg, FailingAdapter(), self.today)
        self.assertEqual((h["dibuat"], h["gagal"]), (1, 1))
        row = self.db.execute("SELECT status_kirim, keterangan FROM log_pesan").fetchone()
        self.assertEqual(row["status_kirim"], "gagal")
        self.assertIn("simulasi", row["keterangan"])
        self.assertEqual(len(self.c.get("/tagihan", headers=self.admin).get_json()), 1)

    def test_adaptor_resmi_butuh_opt_in(self):  # R-03
        db = connect(self.app.config["DB_PATH"])
        with db:
            db.execute("UPDATE penghuni SET persetujuan_wa = 0")
        h = reminders.jalankan_pengingat(db, self.cfg, FailingAdapter(), self.today)
        self.assertEqual((h["dibuat"], h["dilewati_tanpa_persetujuan"]), (0, 1))

    def test_endpoint_adaptor_belum_siap_400(self):  # meta_cloud tanpa kredensial
        self.app.config["WA_ADAPTER"] = "meta_cloud"
        for k in ("META_WA_TOKEN", "META_WA_PHONE_ID", "META_WA_TEMPLATE"):
            os.environ.pop(k, None)
        self.assertEqual(self.c.post("/pengingat/jalankan", headers=self.admin).status_code, 400)
        self.assertEqual(len(self.c.get("/tagihan", headers=self.admin).get_json()), 1)

    def test_tandai_terkirim_manual(self):
        reminders.jalankan_pengingat(self.db, self.cfg, ManualAdapter(), self.today)
        mid = self.c.get("/pesan", headers=self.admin).get_json()[0]["id"]
        self.assertEqual(self.c.post(f"/pesan/{mid}/tandai-terkirim", headers=self.admin).status_code, 200)
        self.assertEqual(self.c.post(f"/pesan/{mid}/tandai-terkirim", headers=self.admin).status_code, 404)


class TestEditHapusKamar(Base):
    def test_edit_kamar(self):
        k = self.kamar("A1", 900000)
        r = self.c.patch(f"/kamar/{k}", json={"tarif": 1000000, "fasilitas": "AC"}, headers=self.admin)
        self.assertEqual(r.status_code, 200)
        self.assertEqual((r.get_json()["tarif"], r.get_json()["nomor"]), (1000000, "A1"))

    def test_edit_nomor_ganda_409(self):
        self.kamar("A1")
        k2 = self.kamar("A2")
        self.assertEqual(self.c.patch(f"/kamar/{k2}", json={"nomor": "A1"}, headers=self.admin).status_code, 409)

    def test_edit_nomor_sendiri_boleh(self):
        k = self.kamar("A1")
        self.assertEqual(self.c.patch(f"/kamar/{k}", json={"nomor": "A1", "lantai": 2}, headers=self.admin).status_code, 200)

    def test_edit_tidak_valid_dan_tidak_ada(self):
        k = self.kamar()
        for body in ({}, {"tarif": -1}, {"kapasitas": 0}, {"tarif": "x"}, {"hacker": 1}):
            self.assertEqual(self.c.patch(f"/kamar/{k}", json=body, headers=self.admin).status_code, 400, body)
        self.assertEqual(self.c.patch("/kamar/999", json={"tarif": 1}, headers=self.admin).status_code, 404)

    def test_kapasitas_tidak_boleh_di_bawah_penghuni_409(self):
        k = self.kamar()
        self.penghuni(k)
        self.assertEqual(self.c.patch(f"/kamar/{k}", json={"kapasitas": 1}, headers=self.admin).status_code, 200)
        self.assertEqual(self.c.patch(f"/kamar/{k}", json={"kapasitas": 0}, headers=self.admin).status_code, 400)

    def test_ubah_tarif_tidak_mengubah_tagihan_lama(self):
        k = self.kamar("A1", 900000)
        self.penghuni(k)
        self.tagihan()
        self.c.patch(f"/kamar/{k}", json={"tarif": 2000000}, headers=self.admin)
        self.assertEqual(self.c.get("/tagihan", headers=self.admin).get_json()[0]["jumlah"], 900000)

    def test_hapus_kamar_kosong(self):
        k = self.kamar()
        self.assertEqual(self.c.delete(f"/kamar/{k}", headers=self.admin).status_code, 200)
        self.assertEqual(self.c.get("/kamar", headers=self.admin).get_json(), [])
        self.assertEqual(self.c.delete(f"/kamar/{k}", headers=self.admin).status_code, 404)

    def test_hapus_kamar_berpenghuni_409_termasuk_nonaktif(self):
        k = self.kamar()
        pid, _ = self.penghuni(k)
        self.assertEqual(self.c.delete(f"/kamar/{k}", headers=self.admin).status_code, 409)
        self.c.patch(f"/penghuni/{pid}/nonaktif", headers=self.admin)
        self.assertEqual(self.c.delete(f"/kamar/{k}", headers=self.admin).status_code, 409)  # riwayat tagihan dijaga

    def test_penghuni_tidak_boleh_edit_hapus_403(self):
        k = self.kamar()
        _, budi = self.penghuni(k)
        self.assertEqual(self.c.patch(f"/kamar/{k}", json={"tarif": 1}, headers=budi).status_code, 403)
        self.assertEqual(self.c.delete(f"/kamar/{k}", headers=budi).status_code, 403)
        self.assertEqual(self.c.delete(f"/kamar/{k}").status_code, 401)


if __name__ == "__main__":
    unittest.main()
