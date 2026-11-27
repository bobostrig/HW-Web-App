"""Run on a computer with Python: python -m unittest discover -s 02_validation."""
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("high_steel_desktop", ROOT / "04_desktop" / "app.py")
APP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(APP)


class CapacityValidation(unittest.TestCase):
    def test_specification_values(self):
        cases = ((50, 20000), (62.5, 16500), (74.99, 13002.8),
                 (75.01, 12998.4), (112, 8040), (150, 5500))
        for radius, expected in cases:
            with self.subTest(radius=radius):
                self.assertAlmostEqual(APP.capacity_at_radius(radius), expected, places=6)

    def test_warning_threshold(self):
        self.assertAlmostEqual(APP.capacity_at_radius(112) * 0.9, 7236)

    def test_radius_is_bounded(self):
        self.assertEqual(APP.scene_radius(-1000), 150)
        self.assertEqual(APP.scene_radius(310), 0)
        self.assertAlmostEqual(APP.scene_radius(310 + 500), 150)

    def test_challenge_load_is_over_tip_capacity_but_safe_at_target(self):
        self.assertGreater(5750, APP.capacity_at_radius(150))
        self.assertLess(5750, APP.capacity_at_radius(123))

    def test_generated_route_extremes_remain_feasible(self):
        for level, layout in enumerate(APP.TOWER_LAYOUTS, start=1):
            for beam_id, (minimum, maximum) in enumerate(APP.BEAM_SPAWN_RANGES, start=1):
                weight = (3250 + 500 * (level - 1) + 250 if beam_id == 1 else
                          4250 + 500 * (level - 1) + 250 if beam_id == 2 else
                          5750 + 250 * (level - 1))
                target_radius = APP.scene_radius(layout["centers"][beam_id - 1])
                for pickup in (minimum, maximum):
                    route_radius = max(APP.scene_radius(pickup), target_radius)
                    self.assertLess(weight, APP.capacity_at_radius(route_radius))


class CheckpointValidation(unittest.TestCase):
    def test_checkpoint_round_trip(self):
        saved = APP.make_checkpoint(3, 47.5, 600, {0, 2})
        self.assertEqual(APP.validate_checkpoint(saved), (3, 47.5, 600, {0, 2}))

    def test_checkpoint_rejects_bad_level_and_targets(self):
        saved = APP.make_checkpoint(3, 47.5, 600, {0, 2})
        saved["level"] = 6
        with self.assertRaises(ValueError):
            APP.validate_checkpoint(saved)
        saved["level"] = 3
        saved["placed_targets"] = [0, 0]
        with self.assertRaises(ValueError):
            APP.validate_checkpoint(saved)


if __name__ == "__main__":
    unittest.main()
