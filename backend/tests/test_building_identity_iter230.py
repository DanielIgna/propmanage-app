"""Iter 230 — Building Identity Graph pilot: Aleea Negoiu 8D → G10.

Unit tests only. No DB mutation of existing records. No Publish/Deploy.
"""
import asyncio
import json

import pytest

from building_identity import (
    SOURCE_CLIENT,
    SOURCE_GOOGLE,
    SOURCE_HARTABLOCURI,
    STATUS_CANDIDATE,
    STATUS_DECLARED,
    STATUS_NEVERIFICAT,
    STATUS_PROBABLE,
    classify_building,
    confirmation_payload,
    hartablocuri_facts,
    identity_profile,
    mongo_candidate_filter,
    parse_query,
    resolve_identity,
    serialize_google_observation,
)
from geocoding import normalize_address
from location_resolver import resolve_property_map_location


def _run(coro):
    return asyncio.run(coro)


G10_ID = "g10pilot000000000000001"


def g10_building():
    return {
        "_id": G10_ID,
        "name": "Bloc G10",
        "address": "Aleea Negoiu nr. 8",
        "city": "Cluj-Napoca",
        "context": {
            "verification_status": "unverified",
            "lat": 46.7495,
            "lng": 23.5510,
            "external_sources": {
                "hartablocuri": {
                    "source_name": "HartaBlocuri",
                    "source_record_id": "hb_g10_negoiu_8",
                    "verification_status": STATUS_NEVERIFICAT,
                    "reference_url": "https://www.hartablocuri.ro",
                    "plan_urls": ["https://www.hartablocuri.ro/planuri/g10"],
                    "raw": {
                        "nume": "Bloc G10",
                        "adresa": "Aleea Negoiu nr. 8",
                        "city": "Cluj-Napoca",
                        "neighborhood": "Mănăștur",
                        "uat": "CJ > municipiu Cluj-Napoca > cartier Mănăștur > Mehedinți",
                        "lat": 46.7495,
                        "lng": 23.5510,
                        "regim_inaltime": "parter + 4 etaje",
                        "lift": "nu",
                        "scari": 4,
                        "niveluri": 5,
                        "apartamente": 40,
                        "construction_year": 1972,
                        "an_finalizare_raw": "1972 estimare",
                        "era": "comunist 1968–1979",
                        "structura": "panouri prefabricate",
                        "proiect": "1963–1972 bloc bară prefabricate",
                    },
                }
            },
        },
    }


GOOGLE_8D = {
    "lat": 46.7496,
    "lng": 23.5511,
    "formatted_address": "Aleea Negoiu 8D, Cluj-Napoca 400676, Romania",
    "google_place_id": "ChIJ_test_negoiu_8d",
    "google_location_type": "ROOFTOP",
    "source": SOURCE_GOOGLE,
    "verification_status": STATUS_NEVERIFICAT,
    "query": "Aleea Negoiu nr. 8D, Cluj-Napoca, 400676, România",
}


class TestParseAndNormalize:
    def test_8d_stair_postal(self):
        q = parse_query("Aleea Negoiu nr. 8D, scara 2", city="Cluj-Napoca", postal_code="400676")
        assert q["house_number"] == "8"
        assert q["suffix"] == "D"
        assert q["stair"] == "2"
        assert q["city"] == "Cluj-Napoca"
        assert q["postal_code"] == "400676"
        assert "negoiu" in q["street_tokens"]
        assert "8D" in normalize_address(q["raw"])

    def test_postal_is_not_house_number(self):
        q = parse_query("Aleea Negoiu nr. 8D, Cluj-Napoca, 400676")
        assert q["house_number"] == "8"
        assert q["suffix"] == "D"
        assert q["postal_code"] == "400676"
        assert q["city"] == "Cluj-Napoca"


class TestMatchG10:
    def test_8d_is_probable_not_confirmed(self):
        q = parse_query("Aleea Negoiu nr. 8D, scara 2", city="Cluj-Napoca", postal_code="400676")
        hit = classify_building(q, g10_building(), google=GOOGLE_8D)
        assert hit is not None
        assert hit["status"] == STATUS_PROBABLE
        assert hit["auto_confirmed"] is False
        assert "street" in hit["matched_by"]
        assert "locality" in hit["matched_by"]
        assert "address_number" in hit["matched_by"]
        assert "external_source" in hit["matched_by"]
        diffs = {d["field"] for d in hit["differences"]}
        assert "address_number" in diffs
        num = next(d for d in hit["differences"] if d["field"] == "address_number")
        assert num["client"] == "8D"
        assert num["hartablocuri"] == "8"

    def test_same_name_alone_is_not_enough(self):
        other = {
            "_id": "other",
            "name": "Bloc G10",
            "address": "Strada Alunului nr. 12",
            "city": "Cluj-Napoca",
            "context": {},
        }
        q = parse_query("Aleea Negoiu nr. 8D", city="Cluj-Napoca")
        assert classify_building(q, other, google=GOOGLE_8D) is None

    def test_same_address_text_without_other_signals_is_candidate(self):
        b = {"_id": "pm-only", "name": "Imobil", "address": "Aleea Negoiu nr. 8D",
             "city": "Cluj-Napoca", "context": {}}
        q = parse_query("Aleea Negoiu nr. 8D", city="Cluj-Napoca")
        hit = classify_building(q, b, google=None)
        assert hit is not None
        assert hit["status"] in (STATUS_CANDIDATE, STATUS_PROBABLE)
        assert hit["auto_confirmed"] is False

    def test_neighbor_on_same_street_is_not_a_candidate(self):
        f6 = {
            "_id": "f6",
            "name": "Bloc F6",
            "address": "Aleea Negoiu nr. 9",
            "city": "Cluj-Napoca",
            "context": {"external_sources": {"hartablocuri": {
                "raw": {"nume": "Bloc F6", "adresa": "Aleea Negoiu nr. 9", "city": "Cluj-Napoca"},
            }}},
        }
        q = parse_query("Aleea Negoiu nr. 8D", city="Cluj-Napoca")
        assert classify_building(q, f6, google=GOOGLE_8D) is None

    def test_other_g10_on_different_street_is_not_a_candidate(self):
        anina = {
            "_id": "anina-g10",
            "name": "Bloc G10",
            "address": "Strada Anina nr. 8",
            "city": "Cluj-Napoca",
            "context": {"external_sources": {"hartablocuri": {
                "raw": {"nume": "Bloc G10", "adresa": "Strada Anina nr. 8", "city": "Cluj-Napoca"},
            }}},
        }
        q = parse_query("Aleea Negoiu nr. 8D", city="Cluj-Napoca")
        assert classify_building(q, anina, google=GOOGLE_8D) is None


class TestResolve:
    def test_resolve_g10_keeps_google_unstored(self, monkeypatch):
        async def fake_geocode(*_a, **_k):
            return dict(GOOGLE_8D)

        monkeypatch.setattr("building_identity.geocode_address", fake_geocode)
        out = _run(resolve_identity(
            [g10_building()],
            address="Aleea Negoiu nr. 8D, scara 2",
            city="Cluj-Napoca",
            postal_code="400676",
            stair="2",
        ))
        assert out["auto_confirmed"] is False
        assert len(out["candidates"]) == 1
        cand = out["candidates"][0]
        assert cand["name"] == "Bloc G10"
        assert cand["status"] == STATUS_PROBABLE
        assert cand["hartablocuri"]["fields"]["apartments"] == 40
        assert cand["hartablocuri"]["fields"]["year_estimated"] == 1972
        assert cand["hartablocuri"]["verification_status"] == STATUS_NEVERIFICAT
        assert cand["prompt"]["actions"] == ["confirm", "reject"]
        google = out["google"]
        assert google["stored"] is False
        assert google["fields"]["formatted_address"].startswith("Aleea Negoiu 8D")
        assert google["fields"]["google_place_id"] == "ChIJ_test_negoiu_8d"

    def test_mongo_filter_requires_street_token(self):
        assert mongo_candidate_filter(parse_query("x")) is None
        filt = mongo_candidate_filter(parse_query("Aleea Negoiu nr. 8D", city="Cluj-Napoca"))
        blob = json.dumps(filt)
        assert "negoiu" in blob
        assert "8" in blob


class TestConfirmationAndProvenance:
    def test_confirm_is_relation_only(self):
        user = {"id": "u1"}
        payload = confirmation_payload(user, "p1", G10_ID, stair="2",
                                       resolver_status=STATUS_PROBABLE,
                                       matched_by=["street", "address_number"])
        link = payload["building_link"]
        assert link["confirmation_source"] == SOURCE_CLIENT
        assert link["confirmation_status"] == STATUS_DECLARED
        assert "property_belongs_to_building" in link["confirmed_fields"]
        assert "construction_year" in link["not_confirmed"]
        assert "structure" in link["not_confirmed"]
        assert payload["observation"]["fields"]["stair"] == "2"
        assert payload["observation"]["verification_status"] == STATUS_DECLARED

    def test_profile_keeps_conflicts_and_unverified_hb(self):
        prop = {
            "_id": "p1",
            "address": "Aleea Negoiu nr. 8D, scara 2",
            "building_id": G10_ID,
            "building_link": {
                "confirmation_source": SOURCE_CLIENT,
                "confirmation_status": STATUS_DECLARED,
                "not_confirmed": ["construction_year"],
            },
        }
        b = g10_building()
        b["context"]["external_sources"]["client"] = {
            "observations": [
                {"source": SOURCE_CLIENT, "property_id": "p1", "fields": {"stair": "2"},
                 "verification_status": STATUS_DECLARED},
                {"source": SOURCE_CLIENT, "property_id": "other-owner", "fields": {"stair": "1"},
                 "verification_status": STATUS_DECLARED},
            ]
        }
        profile = identity_profile(b, property_doc=prop)
        hb = profile["observations"][SOURCE_HARTABLOCURI]
        assert hb["verification_status"] == STATUS_NEVERIFICAT
        assert hb["fields"]["year_estimated"] == 1972
        assert hb["plans"][0]["local_copy"] is False
        assert "hartablocuri.ro" in hb["plans"][0]["url"]
        assert any(c.get("field") == "address" for c in profile["conflicts"])
        mine = [o for o in profile["observations"][SOURCE_CLIENT] if o.get("mine")]
        others = [o for o in profile["observations"][SOURCE_CLIENT] if not o.get("mine")]
        assert mine[0]["property_id"] == "p1"
        assert "property_id" not in others[0]
        assert profile["disclaimer"]
        assert profile["relation"]["confirmation_status"] == STATUS_DECLARED

    def test_confirm_does_not_verify_hb_year(self):
        b = g10_building()
        facts = hartablocuri_facts(b)
        payload = confirmation_payload({"id": "u"}, "p", G10_ID)
        assert facts["fields"]["year_estimated"] == 1972
        assert facts["verification_status"] == STATUS_NEVERIFICAT
        assert "construction_year" in payload["building_link"]["not_confirmed"]


class TestCoordinateFallback:
    def test_derived_from_building_not_copied(self):
        prop = {"address": "Aleea Negoiu nr. 8D"}
        b = g10_building()
        loc = resolve_property_map_location(prop, b)
        assert loc["available"]
        assert loc["derived"] is True
        assert loc["source"] == SOURCE_HARTABLOCURI
        assert loc["verification_status"] == STATUS_NEVERIFICAT
        assert prop.get("lat") is None
        profile = identity_profile(b, property_doc=prop)
        assert profile["display_location"]["derived"] is True

    def test_google_observation_minimized(self):
        obs = serialize_google_observation(GOOGLE_8D)
        assert set(obs["fields"]) <= {
            "lat", "lng", "formatted_address", "google_place_id",
            "google_location_type", "query", "reason",
        }
        assert obs["stored"] is False


import os


@pytest.mark.skipif(not os.environ.get("GOOGLE_MAPS_SERVER_API_KEY"),
                    reason="live geocoding requires GOOGLE_MAPS_SERVER_API_KEY")
class TestLiveGoogleOptional:
    def test_geocode_negoiu_8d_minimized(self):
        from geocoding import geocode_address
        out = _run(geocode_address(
            "Aleea Negoiu nr. 8D", city="Cluj-Napoca", postal_code="400676"))
        obs = serialize_google_observation(out)
        assert obs["stored"] is False
        if out.get("lat") is not None:
            assert 46.6 < out["lat"] < 46.9
            assert 23.4 < out["lng"] < 23.8
