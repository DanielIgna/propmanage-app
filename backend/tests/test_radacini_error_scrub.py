"""Rădăcini — jurnalul de erori nu păstrează date din mesajul excepției (fără backend pornit).

    ./venv/bin/python -m pytest tests/test_radacini_error_scrub.py -q --noconftest
"""
from routes.radacini.common import scrub_error_message


def test_scrub_removes_personal_data():
    msg = scrub_error_message(
        "duplicate key ion.pop@exemplu.ro id 65f1a2b3c4d5e6f7a8b9c0d1 tel +40 722 123 456 value 'Ion Pop'")
    for leak in ("ion.pop", "65f1a2b3", "722", "Ion Pop"):
        assert leak not in msg
    assert msg.startswith("duplicate key <email> id <id> tel <nr> value <valoare>")


def test_scrub_keeps_plain_messages_and_caps_length():
    assert scrub_error_message("division by zero") == "division by zero"
    assert len(scrub_error_message("x" * 2000)) == 300
