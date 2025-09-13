"""Utility functions for the LU-Alert integration."""
from __future__ import annotations

import logging
from typing import List

from shapely.geometry import Point, Polygon
from shapely.errors import ShapelyError

_LOGGER = logging.getLogger(__name__)


def is_point_in_polygons(latitude: float, longitude: float, polygon_strings: List[str]) -> bool:
    """
    Check if a given point is inside any of a list of polygons.

    Args:
        latitude: The latitude of the point.
        longitude: The longitude of the point.
        polygon_strings: A list of strings, where each string is a
                         space-separated list of "lat,lon" coordinates.

    Returns:
        True if the point is inside any of the polygons, False otherwise.
    """
    if not polygon_strings:
        return False

    try:
        point = Point(longitude, latitude)
    except (TypeError, ValueError):
        _LOGGER.warning("Invalid latitude or longitude provided for point.")
        return False

    for poly_str in polygon_strings:
        if not poly_str or not isinstance(poly_str, str):
            continue

        try:
            # 1. Split the string into individual "lat,lon" pairs
            coord_pairs = poly_str.strip().split()

            # 2. Parse each pair into a (longitude, latitude) tuple
            polygon_points = []
            for pair in coord_pairs:
                parts = pair.split(',')
                if len(parts) == 2:
                    try:
                        # Shapely expects (x, y), which is (lon, lat)
                        lat, lon = map(float, parts)
                        polygon_points.append((lon, lat))
                    except (ValueError, TypeError):
                        # Skip malformed coordinate pairs
                        continue

            # A valid polygon needs at least 3 points
            if len(polygon_points) < 3:
                _LOGGER.debug("Skipping polygon with less than 3 valid points.")
                continue

            # 3. Create a Shapely Polygon
            polygon = Polygon(polygon_points)

            # 4. Check if the point is within the polygon
            if polygon.contains(point):
                _LOGGER.debug(
                    "Point (%s, %s) is inside polygon.",
                    latitude,
                    longitude,
                )
                return True

        except ShapelyError as e:
            _LOGGER.warning("Could not create polygon from string '%s': %s", poly_str, e)
        except Exception as e:
            _LOGGER.error("An unexpected error occurred during polygon check: %s", e)

    return False
