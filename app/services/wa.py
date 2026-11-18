"""Adaptor pengiriman pesan (makalah 3.3 dan 3.7): satu operasi kirim(no_wa, teks).
Mengganti opsi pengiriman TIDAK menyentuh aturan tagihan.

STATUS JUJUR:
- ManualAdapter : selalu bisa. Pesan hanya diantrekan; pengelola menekan tombol kirim (tautan wa.me).
- MetaCloudAdapter : jalur resmi WhatsApp Business Platform. BELUM DIUJI; butuh template yang disetujui Meta
  dan opt-in penerima. Jangan dinyatakan 'berhasil kirim' sebelum ada bukti uji.
Library tidak resmi sengaja TIDAK disertakan (risiko blokir nomor, R-02)."""
import json
import os
import urllib.request


class WAError(Exception):
    pass


class ManualAdapter:
    name = "manual"
    butuh_opt_in = False

    def kirim(self, no_wa, teks):
        return "antri"  # menunggu pengelola mengirim sendiri


class MetaCloudAdapter:
    name = "meta_cloud"
    butuh_opt_in = True

    def __init__(self):
        self.token = os.environ.get("META_WA_TOKEN")
        self.phone_id = os.environ.get("META_WA_PHONE_ID")
        self.template = os.environ.get("META_WA_TEMPLATE")  # nama template yang sudah disetujui Meta
        if not (self.token and self.phone_id and self.template):
            raise WAError("META_WA_TOKEN / META_WA_PHONE_ID / META_WA_TEMPLATE belum diatur")

    def kirim(self, no_wa, teks):
        body = {"messaging_product": "whatsapp", "to": no_wa, "type": "template",
                "template": {"name": self.template, "language": {"code": "id"},
                             "components": [{"type": "body", "parameters": [{"type": "text", "text": teks}]}]}}
        req = urllib.request.Request(
            f"https://graph.facebook.com/v20.0/{self.phone_id}/messages", data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status // 100 != 2:
                    raise WAError(f"HTTP {resp.status}")
        except Exception as e:  # jaringan, 4xx/5xx, dll.
            raise WAError(str(e))
        return "terkirim"


def get_adapter(name):
    if name == "manual":
        return ManualAdapter()
    if name == "meta_cloud":
        return MetaCloudAdapter()
    raise WAError(f"adaptor '{name}' tidak dikenal")
