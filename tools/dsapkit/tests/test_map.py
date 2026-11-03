import copy
import unittest

from dsapkit.map.build import _clip, _load_source, check_map, commute_warnings
from dsapkit.map.geometry import Projection, chain, path_d, simplify
from dsapkit.paths import Paths
from dsapkit.site.model import load_site

PATHS = Paths.discover()


class GeometryTest(unittest.TestCase):
    def test_projection_is_metres(self):
        p = Projection(18.6, 73.8)
        x, y = p.metres(73.8, 18.61)
        self.assertAlmostEqual(x, 0)
        self.assertAlmostEqual(y, 1112, delta=2)
        x, _ = p.metres(73.81, 18.6)
        self.assertAlmostEqual(x, 1112 * 0.9478, delta=3)  # shrinks with the cosine of the latitude

    def test_simplify_drops_points_that_do_not_move_the_line(self):
        straight = [(float(i), 0.0) for i in range(10)]
        self.assertEqual(simplify(straight, 0.5), [(0.0, 0.0), (9.0, 0.0)])
        bend = [(0.0, 0.0), (5.0, 0.2), (10.0, 0.0), (15.0, 8.0), (20.0, 0.0)]
        kept = simplify(bend, 0.5)
        self.assertIn((15.0, 8.0), kept)
        self.assertNotIn((5.0, 0.2), kept)

    def test_chain_joins_ways_whatever_their_direction(self):
        a = [(0.0, 0.0), (1.0, 0.0)]
        b = [(2.0, 0.0), (1.0, 0.0)]  # reversed
        c = [(2.0, 0.0), (3.0, 0.0)]
        joined = chain([a, b, c])
        self.assertEqual(len(joined), 1)
        self.assertEqual(sorted(joined[0]), [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)])

    def test_clip_keeps_the_runs_through_the_box(self):
        # Leaves the box, wanders far outside, comes back: two runs, each with one point beyond its edge.
        line = [(-5.0, 0.0), (1.0, 1.0), (2.0, 1.0), (9.0, 9.0), (20.0, 20.0), (30.0, 30.0), (10.0, 10.0), (3.0, 3.0)]
        runs = _clip(line, (0.0, 0.0, 5.0, 5.0))
        self.assertEqual(runs, [[(-5.0, 0.0), (1.0, 1.0), (2.0, 1.0), (9.0, 9.0)], [(10.0, 10.0), (3.0, 3.0)]])
        # A short trip outside, one point each way, stays one run.
        self.assertEqual(len(_clip([(1.0, 1.0), (9.0, 9.0), (20.0, 20.0), (3.0, 3.0)], (0.0, 0.0, 5.0, 5.0))), 1)

    def test_path_d(self):
        self.assertEqual(path_d([(0.0, 0.0), (1.25, 2.0)], 1), "M0.0 0.0L1.2 2.0")


class ConsistencyTest(unittest.TestCase):
    def test_pinned_map_matches_the_areas(self):
        self.assertEqual(check_map(load_site(PATHS), _load_source(PATHS)), [])

    def test_a_missing_route_asks_for_a_new_fetch(self):
        site = load_site(PATHS)
        source = copy.deepcopy(_load_source(PATHS))
        del source["routes"]["aundh"]["wakad"]
        problems = check_map(site, source)
        self.assertTrue(any("aundh" in p and "make map-fetch" in p for p in problems))

    def test_every_area_without_its_own_centre_has_a_route_to_each_centre(self):
        site = load_site(PATHS)
        source = _load_source(PATHS)
        needs_route = {a for a, area in site.areas.items() if not area["commute"].get("localCentre")}
        self.assertEqual(set(source["routes"]), needs_route)
        for by_centre in source["routes"].values():
            self.assertEqual(set(by_centre), set(site.centres))


class CommuteWarningTest(unittest.TestCase):
    LIMITS = {"relative": 0.25, "absoluteKm": 1.0}

    def source(self, km_to: dict[str, float]):
        return {"routes": {"baner": {cid: {"km": km, "line": []} for cid, km in km_to.items()}}}

    def site(self, stated_km: float):
        site = load_site(PATHS)
        site.areas["baner"]["nearestCentre"] = "wakad"
        site.areas["baner"]["commute"]["routes"] = [{"centre": "wakad", "km": stated_km}]
        return site

    def test_quiet_when_the_stated_distance_matches_the_road(self):
        warnings = commute_warnings(self.site(9.0), self.source({"wakad": 9.4, "sangvi-head-office": 9.8}), self.LIMITS)
        self.assertEqual([w for w in warnings if w.startswith("baner")], [])

    def test_a_distance_far_from_the_road_route_is_reported(self):
        warnings = commute_warnings(self.site(5.3), self.source({"wakad": 9.4, "sangvi-head-office": 9.8}), self.LIMITS)
        self.assertTrue(any(w.startswith("baner") and "5.3 km" in w for w in warnings))

    def test_another_centre_nearer_by_road_is_reported(self):
        warnings = commute_warnings(self.site(9.4), self.source({"wakad": 9.4, "sangvi-head-office": 7.8}), self.LIMITS)
        self.assertTrue(any(w.startswith("baner") and "nearer" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
