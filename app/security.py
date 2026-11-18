"""Hash kata sandi (scrypt + salt unik, rekomendasi OWASP bila Argon2id tidak tersedia) dan token stateless."""
import base64
import datetime as dt
import hashlib
import hmac
import os

import jwt


def hash_password(password, n=2 ** 17, r=8, p=1):
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, maxmem=256 * 1024 * 1024, dklen=32)
    b64 = lambda b: base64.b64encode(b).decode()
    return f"scrypt${n}${r}${p}${b64(salt)}${b64(dk)}"


def verify_password(password, stored):
    try:
        algo, n, r, p, salt, dk = stored.split("$")
        if algo != "scrypt":
            return False
        salt, dk = base64.b64decode(salt), base64.b64decode(dk)
        test = hashlib.scrypt(password.encode(), salt=salt, n=int(n), r=int(r), p=int(p),
                              maxmem=256 * 1024 * 1024, dklen=len(dk))
        return hmac.compare_digest(test, dk)
    except Exception:
        return False


def make_token(user_id, role, secret, ttl_hours):
    now = dt.datetime.now(dt.timezone.utc)
    payload = {"sub": str(user_id), "role": role, "iat": now, "exp": now + dt.timedelta(hours=ttl_hours)}
    return jwt.encode(payload, secret, algorithm="HS256")


def read_token(token, secret):
    return jwt.decode(token, secret, algorithms=["HS256"])
