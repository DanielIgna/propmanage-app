"""Faza 4 — National SEO Cluster ENGINE (county-agnostic). Teste discovery + state + gate."""
import seo_clusters as sc
from seo_clusters import discover, _materialize, _slug, MIN_INDEX, MIN_PREPARED, BASE

sc._SITE_URL = "https://propmanage.ro"


def _fact(bid, county="Cluj", locality="Cluj-Napoca", nbh="Mănăștur", era="comunist 1977-1990",
          form="bara", floors=4, family="cf1", profiles=("C1",)):
    from hartablocuri_read_layer import build_truth_layer
    raw = {"judet": county, "city": locality, "neighborhood": nbh, "era": era,
           "regim_inaltime": f"P+{floors}" if floors else None, "proiect": (family and f"{family}d") or "x",
           "structura": "panouri prefabricate"}
    tl = build_truth_layer(raw)
    return {"id": bid, "name": f"Bloc {bid}", "address": "adr", "county": county, "locality": locality,
            "neighborhood": nbh, "era": era, "form": form, "floors": floors, "family": family,
            "profiles": list(profiles), "lat": 46.7, "lng": 23.6, "tl": tl}


def _reg(facts):
    return {c.slug: _materialize(c) for c in discover(facts).values()}


# ─────────── COUNTY-AGNOSTIC / SLUG ───────────
def test_county_agnostic_slugs():
    facts = [_fact(f"c{i}", county="Alba", locality="Alba Iulia") for i in range(35)]
    reg = _reg(facts)
    assert f"{BASE}/alba" in reg
    assert f"{BASE}/alba/alba-iulia" in reg  # engine works for ANY county, no Cluj hardcode


def test_slugs_unique():
    facts = [_fact(f"c{i}") for i in range(40)]
    reg = _reg(facts)
    assert len(reg) == len({c["slug"] for c in reg.values()})


# ─────────── STATE MACHINE ───────────
def test_index_state_strong_substance():
    reg = _reg([_fact(f"c{i}") for i in range(40)])
    loc = reg[f"{BASE}/cluj/cluj-napoca"]
    assert loc["state"] == "INDEX" and loc["index"] is True and loc["in_sitemap"] is True


def test_prepared_state_partial():
    reg = _reg([_fact(f"c{i}") for i in range(15)])  # 10<=n<30
    loc = reg[f"{BASE}/cluj/cluj-napoca"]
    assert loc["state"] == "PREPARED" and loc["index"] is False and loc["in_sitemap"] is False


def test_candidate_state_thin():
    reg = _reg([_fact(f"c{i}") for i in range(5)])  # <10
    loc = reg[f"{BASE}/cluj/cluj-napoca"]
    assert loc["state"] == "CANDIDATE" and loc["index"] is False


def test_only_index_in_sitemap():
    reg = _reg([_fact(f"c{i}") for i in range(40)])
    for c in reg.values():
        if c["in_sitemap"]:
            assert c["state"] == "INDEX"
        if c["state"] != "INDEX":
            assert c["in_sitemap"] is False


# ─────────── DIMENSIONS / COMBOS ───────────
def test_discovers_all_dimensions():
    reg = _reg([_fact(f"c{i}") for i in range(40)])
    dims = {c["dimension"] for c in reg.values()}
    for d in ("county", "locality", "locality_era", "locality_neighborhood", "locality_form",
              "locality_project_family", "locality_typology", "era_typology"):
        assert d in dims, d


def test_no_empty_or_placeholder_clusters():
    # placeholder era/neighborhood must NOT create clusters
    facts = [_fact(f"c{i}", era="necunoscut", nbh="necunoscut", family=None, profiles=()) for i in range(40)]
    reg = _reg(facts)
    slugs = list(reg.keys())
    assert not any("era-necunoscut" in s for s in slugs)
    assert not any("cartier-necunoscut" in s for s in slugs)
    # every materialized cluster has count > 0
    assert all(c["building_count"] > 0 for c in reg.values())


# ─────────── CONTENT / SAFETY ───────────
def test_index_cluster_has_content_model():
    reg = _reg([_fact(f"c{i}") for i in range(40)])
    c = reg[f"{BASE}/cluj/cluj-napoca"]
    ct = c["content"]
    for k in ("title", "h1", "meta_title", "meta_description", "intro", "what_it_means", "what_it_does_not_mean"):
        assert ct.get(k)
    assert len(ct["meta_description"]) <= 300


def test_provenance_and_limits():
    reg = _reg([_fact(f"c{i}") for i in range(40)])
    c = reg[f"{BASE}/cluj/cluj-napoca/tip-panou-prefabricat-p4"]
    assert c["provenance"]["verification_status"] == "neverificat"
    assert c["provenance"]["typology_note"] == "Candidate Typology · derivat din HartaBlocuri"
    joined = " ".join(c["data_limits"]).lower()
    assert "risc seismic" in joined and "energetic" in joined


def test_monetization_touchpoints():
    reg = _reg([_fact(f"c{i}") for i in range(40)])
    c = reg[f"{BASE}/cluj/cluj-napoca"]
    for k in ("free", "lead", "paid", "specialist", "property"):
        assert k in c["monetization"]


def test_internal_link_graph_parents():
    reg = _reg([_fact(f"c{i}") for i in range(40)])
    c = reg[f"{BASE}/cluj/cluj-napoca/era-comunist-1977-1990"]
    assert f"{BASE}/cluj" in c["internal_links"]["parents"]
    assert f"{BASE}/cluj/cluj-napoca" in c["internal_links"]["parents"]


def test_related_guides_real_slugs():
    from seo_guides import GUIDE_SLUGS
    valid = {s for s, _ in GUIDE_SLUGS}
    reg = _reg([_fact(f"c{i}") for i in range(40)])
    c = reg[f"{BASE}/cluj/cluj-napoca"]
    for g in c["internal_links"]["related_guides"]:
        assert g["slug"] in valid
