"""Rădăcini S6-G — fotografii. Unit (fără server) + HTTP (doar cu RADACINI_TEST_STORAGE=1).

Unit: ./venv/bin/python -m pytest tests/test_radacini_s6c.py -q --noconftest -k "not http"
HTTP scriu în storage-ul real: rulează doar cu RADACINI_TEST_STORAGE=1 și REACT_APP_BACKEND_URL.
"""
import io
import os
import sys
import uuid
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from routes.radacini.photos import sanitize_image, sniff_type  # noqa: E402


def _jpeg_with_gps(size=(3000, 2000)) -> bytes:
    im = Image.new("RGB", size, (200, 30, 30))
    exif = Image.Exif()
    exif[0x010F] = "TestCam"
    gps = exif.get_ifd(0x8825)
    gps[1], gps[2], gps[3], gps[4] = "N", (46.0, 46.0, 16.0), "E", (23.0, 37.0, 24.0)
    out = io.BytesIO()
    im.save(out, format="JPEG", exif=exif)
    return out.getvalue()


def test_sanitizer_strips_exif_gps_and_resizes():
    src = _jpeg_with_gps()
    assert Image.open(io.BytesIO(src)).getexif().get_ifd(0x8825), "fixture must carry GPS"
    out, w, h = sanitize_image(src)
    assert max(w, h) <= 1600 and (w, h) == (1600, 1067)
    im = Image.open(io.BytesIO(out))
    assert im.format == "JPEG" and im.size == (w, h)
    assert len(im.getexif()) == 0 and not im.getexif().get_ifd(0x8825)
    assert b"Exif" not in out[:40] and b"TestCam" not in out


@pytest.mark.parametrize("fmt", ["PNG", "WEBP"])
def test_sanitizer_accepts_png_webp_and_small_images_not_upscaled(fmt):
    buf = io.BytesIO()
    Image.new("RGBA", (200, 100), (0, 255, 0, 128)).save(buf, format=fmt)
    out, w, h = sanitize_image(buf.getvalue())
    assert (w, h) == (200, 100) and sniff_type(out) == "image/jpeg"


def test_sanitizer_rejects_non_images():
    for bad in (b"", b"hello world", b"%PDF-1.4 ...", b"<svg></svg>", b"\xff\xd8\xff" + b"garbage" * 10):
        with pytest.raises(ValueError):
            sanitize_image(bad)


def test_sanitizer_rejects_oversize():
    with pytest.raises(ValueError):
        sanitize_image(b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024 + 1))


# ---------------------------------------------------------------- HTTP (storage real)
_http = pytest.mark.skipif(
    os.environ.get("RADACINI_TEST_STORAGE") != "1" or not os.environ.get("REACT_APP_BACKEND_URL"),
    reason="scrie în storage real: setează RADACINI_TEST_STORAGE=1 și REACT_APP_BACKEND_URL",
)


def _login(email, passwords):
    import requests
    api = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
    s = requests.Session()
    for pwd in passwords:
        if s.post(f"{api}/auth/login", json={"email": email, "password": pwd}, timeout=20).status_code == 200:
            return s, api
    pytest.skip(f"login failed for {email}")


@_http
def test_http_photo_permissions():
    owner, api = _login("client@propmanage.io", ["Client123!"])
    other, _ = _login("specialist@propmanage.io", ["Spec123!"])
    import requests
    R = f"{api}/radacini"
    mine = owner.get(f"{R}/parcels/mine", timeout=20).json()
    mine = mine.get("parcels", mine) if isinstance(mine, dict) else mine
    if not mine:
        pytest.skip("niciun teren al proprietarului")
    pid = mine[0]["id"]
    img = io.BytesIO()
    Image.new("RGB", (64, 64), "green").save(img, format="JPEG")
    files = lambda: {"file": (f"{uuid.uuid4().hex}.jpg", img.getvalue(), "image/jpeg")}  # noqa: E731
    r = other.post(f"{R}/photos", data={"target_type": "parcel", "target_id": pid}, files=files(), timeout=30)
    assert r.status_code == 403
    r = owner.post(f"{R}/photos", data={"target_type": "parcel", "target_id": pid}, files=files(), timeout=30)
    assert r.status_code == 201, r.text
    photo_id = r.json()["photo"]["id"]
    try:
        bad = owner.post(f"{R}/photos", data={"target_type": "parcel", "target_id": pid},
                         files={"file": ("x.jpg", b"not an image", "image/jpeg")}, timeout=30)
        assert bad.status_code == 400
        if mine[0].get("status") == "published":
            anon = requests.get(f"{R}/photos", params={"target_type": "parcel", "target_id": pid}, timeout=20)
            assert anon.status_code == 200 and any(p["id"] == photo_id for p in anon.json()["photos"])
            assert requests.get(f"{R}/photos/{photo_id}", timeout=30).headers["content-type"] == "image/jpeg"
        assert other.delete(f"{R}/photos/{photo_id}", timeout=20).status_code == 403
    finally:
        assert owner.delete(f"{R}/photos/{photo_id}", timeout=20).status_code == 200
