"""Point in polygon / circle, in pure Python."""
import unittest

from cap_samples import CITY, ESCH, HOME
from custom_components.lu_alert import geo
from custom_components.lu_alert.model import Area

# an L-shaped (concave) polygon: the notch at the top right is outside
L_SHAPE = "0,0 0,10 5,10 5,5 10,5 10,0 0,0"


class PolygonTests(unittest.TestCase):
    def test_parse_drops_the_closing_point_and_bad_pairs(self):
        ring = geo.parse_polygon(CITY)
        self.assertEqual(len(ring), 4)
        self.assertEqual(geo.parse_polygon("1,1 x,y 2,2 3 3,3 4,4,4 nan,1"), [(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)])
        self.assertEqual(geo.parse_polygon("1,1 2,2"), [])
        self.assertEqual(geo.parse_polygon(""), [])

    def test_inside_and_outside(self):
        ring = geo.parse_polygon(CITY)
        self.assertTrue(geo.in_polygon(HOME[0], HOME[1], ring))
        self.assertFalse(geo.in_polygon(49.4958, 5.9806, ring))             # Esch-sur-Alzette
        self.assertFalse(geo.in_polygon(0, 0, ring))

    def test_a_concave_polygon(self):
        ring = geo.parse_polygon(L_SHAPE)
        self.assertTrue(geo.in_polygon(2, 2, ring))
        self.assertTrue(geo.in_polygon(8, 2, ring))
        self.assertTrue(geo.in_polygon(2, 8, ring))
        self.assertFalse(geo.in_polygon(8, 8, ring))                         # in the notch

    def test_the_border_counts_as_inside(self):
        ring = geo.parse_polygon("0,0 0,10 10,10 10,0")
        for point in ((0, 5), (5, 0), (10, 10), (0, 0), (10, 5)):
            self.assertTrue(geo.in_polygon(point[0], point[1], ring), point)
        self.assertFalse(geo.in_polygon(10.0001, 5, ring))

    def test_the_point_in_the_ring_is_independent_of_the_winding(self):
        ring = geo.parse_polygon(CITY)
        self.assertEqual(geo.in_polygon(HOME[0], HOME[1], ring), geo.in_polygon(HOME[0], HOME[1], ring[::-1]))


class CircleTests(unittest.TestCase):
    def test_inside_and_outside_in_kilometres(self):
        self.assertTrue(geo.in_circle(49.6116, 6.1319, "49.6116,6.1319 1"))
        self.assertTrue(geo.in_circle(49.62, 6.13, "49.6116,6.1319 2"))             # about 1 km away
        self.assertFalse(geo.in_circle(49.4958, 5.9806, "49.6116,6.1319 5"))        # Esch is about 20 km away
        self.assertTrue(geo.in_circle(49.4958, 5.9806, "49.6116,6.1319 25"))

    def test_the_distance(self):
        self.assertAlmostEqual(geo.distance_km(49.6116, 6.1319, 49.4958, 5.9806), 17.0, delta=1.5)
        self.assertEqual(geo.distance_km(1, 1, 1, 1), 0.0)

    def test_text_that_is_not_a_circle(self):
        for text in ("", "49,6", "49,6 x", "49,6 -1", "a,b 3", "49 6 3", "nan,1 2"):
            self.assertIsNone(geo.in_circle(49, 6, text), text)


class LocateTests(unittest.TestCase):
    def test_three_valued(self):
        city, esch = Area("City", polygons=(CITY,)), Area("Esch", polygons=(ESCH,))
        self.assertIs(geo.locate(HOME[0], HOME[1], [esch, city]), True)
        self.assertIs(geo.locate(HOME[0], HOME[1], [esch]), False)
        self.assertIsNone(geo.locate(HOME[0], HOME[1], [Area("Luxembourg")]))        # a name only: no answer
        self.assertIsNone(geo.locate(HOME[0], HOME[1], []))
        self.assertIsNone(geo.locate(HOME[0], HOME[1], [Area("x", polygons=("garbage",))]))

    def test_circles_and_polygons_mix(self):
        areas = [Area("a", polygons=(ESCH,), circles=("49.6116,6.1319 3",))]
        self.assertIs(geo.locate(HOME[0], HOME[1], areas), True)

    def test_an_area_with_only_garbage_geometry_does_not_hide_a_good_one(self):
        areas = [Area("bad", polygons=("zzz",)), Area("good", polygons=(CITY,))]
        self.assertIs(geo.locate(HOME[0], HOME[1], areas), True)


if __name__ == "__main__":
    unittest.main()
