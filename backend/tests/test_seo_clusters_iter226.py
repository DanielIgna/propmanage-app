"""Faza 3 — HartaBlocuri SEO Cluster Foundation (read-only). Teste taxonomy + engine."""
import seo_clusters as sc
from seo_clusters import (
    _slugify, build_cluster, PILOT_CLUSTERS, pilot_slugs, _build_content, _quality_gate,
)

# evită importul routes.public în teste (self-canonical determinist)
sc._SITE_URL = "https://propmanage.ro"


def _b(city="Cluj-Napoca", era="comunist 1977-1990", structura="panouri prefabricate",
       regim="P+4", proiect="cf1d", nbh="Mănăștur", bid="x1"):
    raw = {"era": era, "structura": structura, "regim_inaltime": regim, "proiect": proiect,
           "neighborhood": nbh, "city": city}
    from hartablocuri_read_layer import build_truth_layer
    return {"id": bid, "city": city, "raw": raw, "tl": build_truth_layer(raw), "neighborhood": nbh}


C1 = next(c for c in PILOT_CLUSTERS if c["id"] == "cluj-panou-p4")
ERA_C = next(c for c in PILOT_CLUSTERS if c["id"] == "cluj-comunist-1977-1990")
FAM_C = next(c for c in PILOT_CLUSTERS if c["id"] == "cluj-proiect-cf1")


# ─────────── TAXONOMY / SLUG ───────────
def test_slugify_diacritics():
    assert _slugify("Cluj-Napoca") == "cluj-napoca"
    assert _slugify("interbelic/antebelic") == "interbelic-antebelic"


def test_pilot_slugs_unique():
    slugs = pilot_slugs()
    assert len(slugs) == len(set(slugs)) == 5


def test_no_duplicate_cluster_ids():
    ids = [c["id"] for c in PILOT_CLUSTERS]
    assert len(ids) == len(set(ids))


# ─────────── AGGREGATION (real, no fabrication) ───────────
def test_aggregate_counts_real():
    buildings = [_b(bid=f"c{i}") for i in range(30)] + [_b(city="Turda", bid="t1")]
    c = build_cluster(C1, buildings)
    # only Cluj-Napoca matches locality + C1 profile
    assert c["aggregates"]["building_count"] == 30
    assert c["aggregates"]["localities"] == [{"name": "Cluj-Napoca", "count": 30}]


def test_no_empty_cluster_fabrication():
    # zero matching buildings → count 0, gate fails, no invented stats
    c = build_cluster(C1, [_b(era="post-1990", structura="beton", regim="P+8", bid="p1")])
    assert c["aggregates"]["building_count"] == 0
    assert c["quality_gate"]["passes"] is False
    assert c["aggregates"]["era_distribution"] == []


def test_era_cluster_matches_only_era():
    buildings = [_b(era="comunist 1977-1990", bid="a"), _b(era="post-1990", bid="b")]
    c = build_cluster(ERA_C, buildings)
    assert c["aggregates"]["building_count"] == 1


def test_family_cluster_matches_family():
    buildings = [_b(proiect="bloc cf1d", bid="a"), _b(proiect="cf3sd 18x9m", bid="b")]
    c = build_cluster(FAM_C, buildings)
    assert c["aggregates"]["building_count"] == 1


# ─────────── METADATA / CANONICAL ───────────
def test_metadata_present_and_real():
    buildings = [_b(bid=f"c{i}") for i in range(40)]
    c = build_cluster(C1, buildings)
    ct = c["content"]
    assert ct["title"] and ct["meta_title"] and ct["meta_description"] and ct["h1"] and ct["intro"]
    assert "40" in ct["title"]  # count is real, from aggregate
    assert len(ct["meta_description"]) <= 300


def test_canonical_self():
    buildings = [_b(bid=f"c{i}") for i in range(30)]
    c = build_cluster(C1, buildings)
    assert c["canonical"] == "https://propmanage.ro/blocuri/cluj-napoca/panou-prefabricat-p4"
    assert c["slug"] == "/blocuri/cluj-napoca/panou-prefabricat-p4"


# ─────────── SAFETY: NOT PUBLISHED / NOINDEX / PROVENANCE ───────────
def test_never_indexed_or_in_sitemap():
    c = build_cluster(C1, [_b(bid=f"c{i}") for i in range(50)])
    assert c["index"] is False
    assert c["in_sitemap"] is False
    assert c["published"] is False
    assert c["status"] == "pilot_prepared"
    assert c["indexability"] == "prepared_noindex"


def test_provenance_and_candidate_note():
    c = build_cluster(C1, [_b(bid=f"c{i}") for i in range(30)])
    p = c["provenance"]
    assert p["source"] == "hartablocuri"
    assert p["verification_status"] == "neverificat"
    assert "neverificate de PropManage" in p["verification_note"]
    # C1 is L2 candidate typology
    assert p["typology_note"] == "Candidate Typology · derivat din HartaBlocuri"


def test_no_professional_inference_in_limits():
    c = build_cluster(C1, [_b(bid=f"c{i}") for i in range(30)])
    joined = " ".join(c["data_limits"]).lower()
    assert "neverificate de propmanage" in joined
    assert "risc seismic" in joined and "clasă energetică" in joined  # explicit disclaimers


def test_quality_gate_threshold():
    assert _quality_gate({"building_count": 25, "localities": [{"name": "x", "count": 25}]})["passes"] is True
    assert _quality_gate({"building_count": 24, "localities": [{"name": "x", "count": 24}]})["passes"] is False


# ─────────── INTERNAL LINKING ───────────
def test_internal_links_forward_targets_exist():
    c = build_cluster(C1, [_b(bid=f"c{i}") for i in range(30)])
    hrefs = {l["href"] for l in c["internal_links"]["forward"]}
    assert "/cartea-casei" in hrefs and "/scorul-casei" in hrefs and "/digital-twin" in hrefs


def test_related_guides_are_real_slugs():
    from seo_guides import GUIDE_SLUGS
    valid = {s for s, _ in GUIDE_SLUGS}
    c = build_cluster(C1, [_b(bid=f"c{i}") for i in range(30)])
    for g in c["internal_links"]["related_guides"]:
        assert g["slug"] in valid
