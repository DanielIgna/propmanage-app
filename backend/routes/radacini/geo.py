"""Helpere geografice Rădăcini: distanță, validarea poligonului și suprafața sferică."""
import math
from typing import Optional

EARTH_RADIUS_KM = 6371.0088
EARTH_RADIUS_M = EARTH_RADIUS_KM * 1000
LAT_MIN, LAT_MAX = 43.5, 48.5
LNG_MIN, LNG_MAX = 20.0, 30.0
MIN_VERTICES, MAX_VERTICES = 3, 100
KM_PER_DEG_LAT = 111.32


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dl = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def bbox(lat: float, lng: float, radius_km: float, margin_deg: float = 0.0) -> tuple[float, float, float, float]:
    """(lat_min, lat_max, lng_min, lng_max) care cuprinde cercul; `margin_deg` extinde dreptunghiul."""
    dlat = radius_km / KM_PER_DEG_LAT
    cos = max(math.cos(math.radians(lat)), 0.01)
    dlng = radius_km / (KM_PER_DEG_LAT * cos)
    return lat - dlat - margin_deg, lat + dlat + margin_deg, lng - dlng - margin_deg, lng + dlng + margin_deg


def in_romania_bbox(lat: float, lng: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX


def _orient(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(a, b, p) -> bool:
    return min(a[0], b[0]) <= p[0] <= max(a[0], b[0]) and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])


def _segments_intersect(p1, p2, p3, p4) -> bool:
    d1, d2 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    d3, d4 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    if ((d1 > 0 > d2) or (d1 < 0 < d2)) and ((d3 > 0 > d4) or (d3 < 0 < d4)):
        return True
    return (
        (d1 == 0 and _on_segment(p3, p4, p1)) or (d2 == 0 and _on_segment(p3, p4, p2))
        or (d3 == 0 and _on_segment(p1, p2, p3)) or (d4 == 0 and _on_segment(p1, p2, p4))
    )


def _self_intersects(ring: list) -> bool:
    """`ring` fără punctul de închidere. Muchiile neadiacente nu au voie să se atingă; cele adiacente nu
    au voie să se suprapună (puncte coliniare întoarse pe aceeași direcție)."""
    n = len(ring)
    for i in range(n):
        a, b = ring[i], ring[(i + 1) % n]
        for j in range(i + 1, n):
            if j == i + 1 or (i == 0 and j == n - 1):
                # adiacente: se suprapun doar dacă al treilea punct e coliniar și în interiorul muchiei
                c = ring[(j + 1) % n] if j == i + 1 else ring[(i - 1) % n]
                shared = ring[j] if j == i + 1 else ring[i]
                other = a if j == i + 1 else b
                if _orient(other, shared, c) == 0 and _on_segment(other, shared, c) and c != shared:
                    return True
                continue
            if _segments_intersect(a, b, ring[j], ring[(j + 1) % n]):
                return True
    return False


def spherical_area_m2(ring: list) -> float:
    """Suprafața (m²) a unui inel [[lng, lat], ...] fără punct de închidere, pe sferă."""
    n = len(ring)
    total = 0.0
    for i in range(n):
        lng1, lat1 = ring[i]
        lng2, lat2 = ring[(i + 1) % n]
        total += math.radians(lng2 - lng1) * (2 + math.sin(math.radians(lat1)) + math.sin(math.radians(lat2)))
    return abs(total) * EARTH_RADIUS_M ** 2 / 2


def validate_polygon(geometry) -> tuple[dict, float]:
    """Validează un GeoJSON Polygon (un singur inel exterior). Întoarce (geometrie normalizată cu inelul închis,
    suprafața în m²). ValueError cu mesaj în română."""
    if not isinstance(geometry, dict) or geometry.get("type") != "Polygon":
        raise ValueError("Poligonul trebuie să fie un GeoJSON de tip Polygon.")
    coords = geometry.get("coordinates")
    if not isinstance(coords, list) or len(coords) != 1 or not isinstance(coords[0], list):
        raise ValueError("Poligonul trebuie să aibă un singur contur (fără goluri).")
    raw = coords[0]
    if len(raw) > MAX_VERTICES + 1:
        raise ValueError(f"Poligonul are cel mult {MAX_VERTICES} de vârfuri.")
    ring: list = []
    for pt in raw:
        if (
            not isinstance(pt, (list, tuple)) or len(pt) < 2
            or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in pt[:2])
        ):
            raise ValueError("Vârf invalid: așteptat [longitudine, latitudine].")
        ring.append([float(pt[0]), float(pt[1])])
    if len(ring) >= 2 and ring[0] == ring[-1]:
        ring.pop()
    if not MIN_VERTICES <= len(ring) <= MAX_VERTICES:
        raise ValueError(f"Poligonul trebuie să aibă între {MIN_VERTICES} și {MAX_VERTICES} vârfuri.")
    if any(not in_romania_bbox(lat, lng) for lng, lat in ring):
        raise ValueError("Poligonul este în afara zonei Rădăcini.")
    if len({tuple(p) for p in ring}) != len(ring):
        raise ValueError("Poligonul are vârfuri repetate.")
    if _self_intersects(ring):
        raise ValueError("Poligonul se intersectează cu el însuși.")
    area = spherical_area_m2(ring)
    if area < 1:
        raise ValueError("Poligonul nu are suprafață.")
    return {"type": "Polygon", "coordinates": [ring + [ring[0]]]}, round(area, 1)


def area_warning(geometry_area_m2: Optional[float], area_m2: Optional[float]) -> Optional[str]:
    """Avertisment dacă suprafața desenată diferă cu peste 30% de cea declarată."""
    if not geometry_area_m2 or not area_m2:
        return None
    if abs(geometry_area_m2 - area_m2) / area_m2 > 0.30:
        return (
            f"Suprafața desenată (~{round(geometry_area_m2):,} m²) diferă cu peste 30% "
            f"de cea declarată ({round(area_m2):,} m²).".replace(",", " ")
        )
    return None
