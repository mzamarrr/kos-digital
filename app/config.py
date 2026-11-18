"""Konfigurasi. Semua aturan yang MASIH BELUM PASTI (makalah Bagian 3.1/3.6) dibuat sebagai parameter,
bukan ditanam di kode. Ubah lewat variabel lingkungan setelah pengelola kos memberi keputusan."""
import os
import secrets

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _env_bool(name, default):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes")


class Config:
    DB_PATH = os.environ.get("KOS_DB", os.path.join(BASE_DIR, "kos.db"))
    UPLOAD_DIR = os.environ.get("KOS_UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))

    # Keamanan
    SECRET_KEY = os.environ.get("KOS_SECRET") or secrets.token_hex(32)  # set KOS_SECRET di produksi
    TOKEN_TTL_HOURS = 8
    SCRYPT_N = int(os.environ.get("KOS_SCRYPT_N", 2 ** 17))  # OWASP: N=2^17, r=8, p=1

    # Unggah bukti (batas belum ditetapkan di makalah -> parameter)
    MAX_UPLOAD_BYTES = int(os.environ.get("KOS_MAX_UPLOAD", 2 * 1024 * 1024))
    ALLOWED_EXT = {"jpg", "jpeg", "png", "pdf"}

    # Aturan tagihan (BELUM DIKONFIRMASI pengelola)
    BILLING_CYCLE = os.environ.get("KOS_CYCLE", "calendar")  # "calendar" | "per_penghuni"
    DUE_DAY = int(os.environ.get("KOS_DUE_DAY", 10))          # tanggal jatuh tempo (mode calendar)
    PRORATA = _env_bool("KOS_PRORATA", False)                 # pro-rata penghuni masuk tengah bulan
    REMINDER_DAYS_BEFORE = int(os.environ.get("KOS_REMIND_DAYS", 3))

    # Pengiriman pesan: "manual" (aman, default) | "meta_cloud" (resmi, BELUM DIUJI)
    WA_ADAPTER = os.environ.get("KOS_WA", "manual")

    # Jadwal harian proses scheduler (jam lokal server)
    SCHEDULE_HOUR = int(os.environ.get("KOS_SCHEDULE_HOUR", 7))
