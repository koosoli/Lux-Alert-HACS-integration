"""Is a point inside the area of an alert? Pure Python, no shapely.

CAP writes a polygon as ``lat,lon lat,lon ...`` (first point repeated at the end) and a circle as ``lat,lon radius``
with the radius in kilometres. Luxembourg is small, so a flat ray-casting test on (lon, lat) is exact enough: a
polygon edge is a straight line in the plane of the coordinates, which is also how CAP defines it.
"""
import math
from typing import Iterable, List, Optional, Tuple

from .model import Area

Point = Tuple[float, float]             # (lat, lon)
EARTH_RADIUS_KM = 6371.0088


def parse_polygon(text: str) -> List[Point]:
    """The points of a CAP polygon; pairs that are not numbers are skipped. [] when fewer than 3 points remain."""
    points: List[Point] = []
    for pair in text.split():
        parts = pair.split(",")
        if len(parts) != 2:
            continue
        try:
            lat, lon = float(parts[0]), float(parts[1])
        except ValueError:
            continue
        if math.isfinite(lat) and math.isfinite(lon):
            points.append((lat, lon))
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    return points if len(points) >= 3 else []


def in_polygon(lat: float, lon: float, ring: List[Point]) -> bool:
    """Ray casting; a point on the border counts as inside."""
    inside = False
    count = len(ring)
    for i in range(count):
        lat1, lon1 = ring[i]
        lat2, lon2 = ring[(i + 1) % count]
        # on the edge: collinear and within its bounding box
        cross = (lon2 - lon1) * (lat - lat1) - (lat2 - lat1) * (lon - lon1)
        if (abs(cross) < 1e-12 and min(lat1, lat2) - 1e-12 <= lat <= max(lat1, lat2) + 1e-12
                and min(lon1, lon2) - 1e-12 <= lon <= max(lon1, lon2) + 1e-12):
            return True
        if (lat1 > lat) != (lat2 > lat):
            crossing_lon = lon1 + (lat - lat1) * (lon2 - lon1) / (lat2 - lat1)
            if lon < crossing_lon:
                inside = not inside
    return inside


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((phi2 - phi1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def in_circle(lat: float, lon: float, text: str) -> Optional[bool]:
    """``lat,lon radius`` -> True/False; None when the text is not a circle."""
    parts = text.split()
    if len(parts) != 2:
        return None
    centre = parts[0].split(",")
    if len(centre) != 2:
        return None
    try:
        clat, clon, radius = float(centre[0]), float(centre[1]), float(parts[1])
    except ValueError:
        return None
    if not all(math.isfinite(v) for v in (clat, clon, radius)) or radius < 0:
        return None
    return distance_km(lat, lon, clat, clon) <= radius


def locate(lat: float, lon: float, areas: Iterable[Area]) -> Optional[bool]:
    """True: the point is inside one of the areas. False: the areas have geometry and it is outside all of them.
    None: no area has a usable polygon or circle (only a name or a code), so nothing can be said."""
    usable = False
    for area in areas:
        for text in area.polygons:
            ring = parse_polygon(text)
            if ring:
                usable = True
                if in_polygon(lat, lon, ring):
                    return True
        for text in area.circles:
            result = in_circle(lat, lon, text)
            if result is not None:
                usable = True
                if result:
                    return True
    return False if usable else None
