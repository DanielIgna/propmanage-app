"""Iter 231 — guard against creating a Building from Property/entrance granularity.

No DB writes to existing records. HartaBlocuri import untouched.
"""
from building_identity import (
    address_has_unit_granularity,
    detect_unit_granularity,
    granular_create_guard,
)


class TestGranularityDetection:
    def test_negoiu_8d_sc_ap_is_granular(self):
        g = detect_unit_granularity("Aleea Negoiu nr 8D sc 2 ap 25")
        assert g["is_granular"] is True
        assert g["has_stair"] is True
        assert g["has_apartment"] is True
        assert g["stair"] == "2"
        assert g["apartment"] == "25"

    def test_negoiu_nr_8_is_building_level(self):
        assert address_has_unit_granularity("Aleea Negoiu nr 8") is False
        assert address_has_unit_granularity("Aleea Negoiu nr. 8") is False

    def test_bloc_g10_is_building_level(self):
        assert address_has_unit_granularity("Bloc G10", "Aleea Negoiu nr 8") is False

    def test_scarisioara_is_not_stair(self):
        g = detect_unit_granularity("Strada Scărișoara nr 10")
        assert g["is_granular"] is False
        assert g["has_stair"] is False

    def test_dotted_forms(self):
        g = detect_unit_granularity("Aleea Negoiu nr. 8D, sc. 2, ap. 25")
        assert g["is_granular"]
        assert g["stair"] == "2"
        assert g["apartment"] == "25"

    def test_apartamentul_word(self):
        g = detect_unit_granularity("apartamentul 25 scara 2")
        assert g["has_apartment"] and g["has_stair"]
        assert g["apartment"] == "25"
        assert g["stair"] == "2"


class TestGuardDoesNotCreate:
    def test_guard_payload_is_not_a_create(self):
        # Sync contract: granular → guard object, never an insert instruction.
        g = detect_unit_granularity("Aleea Negoiu nr 8D sc 2 ap 25")
        assert g["is_granular"]
        # granular_create_guard is async + DB; detection is the gate that blocks insert.

    def test_import_module_untouched_markers(self):
        from hartablocuri_import import EXCLUDED_ERA, SOURCE_NAME
        assert "STERGE" in EXCLUDED_ERA
        assert SOURCE_NAME == "HartaBlocuri"


class TestGuardAsyncNoInsert:
    def test_granular_returns_created_false(self, monkeypatch):
        import asyncio

        async def fake_resolve(*_a, **_k):
            return {
                "candidates": [
                    {"building_id": "g10", "name": "Bloc G10", "address": "Aleea Negoiu nr. 8",
                     "status": "probable", "auto_confirmed": False},
                    {"building_id": "pm8d", "name": "Negoiu 8 D sc 2",
                     "address": "Aleea Negoiu nr 8 D sc 2", "status": "probable",
                     "auto_confirmed": False},
                ],
                "auto_confirmed": False,
            }

        monkeypatch.setattr("building_identity.resolve_from_db", fake_resolve)

        async def _run():
            return await granular_create_guard(
                None, name="ap 25", address="Aleea Negoiu nr 8D sc 2 ap 25")

        out = asyncio.run(_run())
        assert out["created"] is False
        assert out["auto_confirmed"] is False
        assert out["code"] == "granular_address_needs_choice"
        assert "candidate" in out["message"].lower() or "Alege" in out["message"]
        assert out["granularity"]["stair"] == "2"
        assert out["granularity"]["apartment"] == "25"
        assert len(out["candidates"]) == 2

    def test_granular_no_candidates(self, monkeypatch):
        import asyncio

        async def fake_resolve(*_a, **_k):
            return {"candidates": [], "auto_confirmed": False}

        monkeypatch.setattr("building_identity.resolve_from_db", fake_resolve)
        out = asyncio.run(granular_create_guard(
            None, name="Bloc", address="Aleea Negoiu nr 8D sc 2 ap 25"))
        assert out["created"] is False
        assert out["candidates"] == []
        assert out["code"] == "granular_address_needs_building"

    def test_building_level_not_blocked(self):
        import asyncio
        out = asyncio.run(granular_create_guard(
            None, name="Bloc G10", address="Aleea Negoiu nr. 8"))
        assert out is None
