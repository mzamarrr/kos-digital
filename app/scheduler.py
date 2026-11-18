"""Penjadwal: proses terpisah yang memanggil fungsi layanan yang SAMA dengan endpoint (aturan tagihan di satu tempat).
Tidak butuh token karena tidak lewat HTTP.

  python -m app.scheduler --once     # jalankan sekali (cocok untuk cron / Task Scheduler)
  python -m app.scheduler            # loop harian pada jam KOS_SCHEDULE_HOUR
"""
import argparse
import datetime as dt
import time

from .config import Config
from .db import connect, init_db
from .services import billing, reminders, wa


def jalankan_sekali(cfg=None, today=None):
    cfg = cfg or {k: getattr(Config, k) for k in dir(Config) if k.isupper()}
    today = today or dt.date.today()
    init_db(cfg["DB_PATH"])
    db = connect(cfg["DB_PATH"])
    try:
        # 1) tagihan (idempoten) -- tidak bergantung pada pengiriman pesan
        gen = billing.generate_tagihan(db, today.strftime("%Y-%m"), cfg)
        print(f"[{today}] tagihan: {gen}")
        # 2) pengingat -- kegagalan di sini tidak membatalkan langkah 1
        try:
            hasil = reminders.jalankan_pengingat(db, cfg, wa.get_adapter(cfg["WA_ADAPTER"]), today)
            print(f"[{today}] pengingat: {hasil}")
        except wa.WAError as e:
            print(f"[{today}] pengingat dilewati, adaptor belum siap: {e}")
        return gen
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if args.once:
        jalankan_sekali()
        return
    last = None
    while True:
        now = dt.datetime.now()
        if now.hour >= Config.SCHEDULE_HOUR and last != now.date():
            jalankan_sekali()
            last = now.date()
        time.sleep(60)


if __name__ == "__main__":
    main()
