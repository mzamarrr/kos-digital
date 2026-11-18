"""Skrip untuk mereset basis data dan folder unggahan,
lalu mengisi ulang data awal (seed) sebelum presentasi demo.

Jalankan dengan:
  python reset_demo.py
"""
import os
from app.config import Config
import seed


def reset():
    # 1. Hapus berkas basis data SQLite lama jika ada
    if os.path.exists(Config.DB_PATH):
        try:
            os.remove(Config.DB_PATH)
            print(f"Basis data lama dihapus: {Config.DB_PATH}")
        except OSError as e:
            print(f"Peringatan: Gagal menghapus database ({e}).")

    # 2. Bersihkan berkas bukti pembayaran di folder uploads/
    if os.path.exists(Config.UPLOAD_DIR):
        for f in os.listdir(Config.UPLOAD_DIR):
            fp = os.path.join(Config.UPLOAD_DIR, f)
            try:
                if os.path.isfile(fp):
                    os.remove(fp)
            except OSError as e:
                print(f"Peringatan: Gagal menghapus berkas {fp} ({e}).")
        print(f"Folder uploads dibersihkan: {Config.UPLOAD_DIR}")
    else:
        os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

    # 3. Jalankan kembali seeder data awal
    seed.main()
    print("\n[OK] Reset demo selesai! Data kembali ke kondisi awal fiktif.")
    print("Akun: admin/admin12345, budi/budi12345, sari/sari12345")


if __name__ == "__main__":
    reset()
