"""Run on a computer with Python: python -m unittest discover -s 02_validation."""
import importlib.util
import json
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

    def test_capacity_interpolation_proportionality(self):
        for (r0, c0), (r1, c1) in zip(APP.CAPACITY_CHART, APP.CAPACITY_CHART[1:]):
            for fraction in (0.25, 0.5, 0.75):
                with self.subTest(segment=(r0, r1), fraction=fraction):
                    radius = r0 + fraction * (r1 - r0)
                    expected = c0 + fraction * (c1 - c0)
                    self.assertAlmostEqual(APP.capacity_at_radius(radius), expected, places=8)

    def test_trolley_radius_and_capacity_are_symmetric(self):
        for offset in (25, 75, 150, 300):
            with self.subTest(offset=offset):
                left = APP.scene_radius(APP.MAST_PIVOT - offset)
                right = APP.scene_radius(APP.MAST_PIVOT + offset)
                self.assertAlmostEqual(left, right, places=8)
                self.assertAlmostEqual(APP.capacity_at_radius(left), APP.capacity_at_radius(right), places=8)

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
        saved = APP.make_checkpoint(3, 47.5, 600, {0, 2}, {0: 3, 2: 1})
        self.assertEqual(APP.validate_checkpoint(json.loads(json.dumps(saved))),
                         (3, 47.5, 600, {0, 2}, {0: 3, 2: 1}))

    def test_older_checkpoint_without_beam_mapping_still_loads(self):
        saved = APP.make_checkpoint(3, 47.5, 600, {0, 2})
        del saved["placements"]
        self.assertEqual(APP.validate_checkpoint(saved), (3, 47.5, 600, {0, 2}, {0: 1, 2: 3}))

    def test_checkpoint_rejects_bad_level_and_targets(self):
        saved = APP.make_checkpoint(3, 47.5, 600, {0, 2})
        saved["level"] = 6
        with self.assertRaises(ValueError):
            APP.validate_checkpoint(saved)
        saved["level"] = 3
        saved["placed_targets"] = [0, 0]
        with self.assertRaises(ValueError):
            APP.validate_checkpoint(saved)

    def test_checkpoint_rejects_unplayable_or_malformed_progress(self):
        for changes in ({"remaining_seconds": 0}, {"remaining_seconds": 120},
                        {"placed_targets": [0, 1, 2]}, {"placed_targets": [True]},
                        {"score": True}, {"version": 99},
                        {"placements": [{"target": 0, "beam_id": 1}, {"target": 2, "beam_id": 1}]},
                        {"placements": [{"target": 0, "beam_id": 1}]},
                        {"placements": [{"target": 0, "beam_id": True}, {"target": 2, "beam_id": 3}]}):
            with self.subTest(changes=changes):
                saved = APP.make_checkpoint(3, 47.5, 600, {0, 2})
                saved.update(changes)
                with self.assertRaises(ValueError):
                    APP.validate_checkpoint(saved)


class GameplayFlowValidation(unittest.TestCase):
    def test_crane_mirror_is_reversible_and_reaches_left_beam(self):
        for x in (190, 221, 286, 334, 465, 817):
            with self.subTest(x=x):
                mirrored = APP.crane_scene_x(x, -1)
                self.assertAlmostEqual(APP.crane_scene_x(mirrored, -1), x)
        self.assertEqual(APP.crane_scene_x(465, -1), 155)
        self.assertEqual(APP.crane_scene_x(415, -1), 205)

    def test_crane_turn_passes_through_edge_on_midpoint(self):
        self.assertAlmostEqual(APP.crane_turn_scale(1, -1, 0), 1)
        self.assertAlmostEqual(APP.crane_turn_scale(1, -1, 0.5), 0)
        self.assertAlmostEqual(APP.crane_turn_scale(1, -1, 1), -1)
        self.assertGreater(APP.crane_turn_scale(1, -1, 0.25),
                           APP.crane_turn_scale(1, -1, 0.75))

    def test_blocked_target_retains_beam(self):
        app = APP.HighSteelApp.__new__(APP.HighSteelApp)
        app.turn_started = 0
        app.carried = 0
        app.beams = [{"id": 1, "state": "carried", "weight": 3250}]
        messages = []
        app._target_under_load = lambda: 0
        app._set_message = messages.append
        app._auto_blocks_target = lambda index: True
        app.toggle_beam()
        self.assertEqual(app.carried, 0)
        self.assertEqual(app.beams[0]["state"], "carried")
        self.assertIn("blocking", messages[0])

    def test_automatic_crane_blocks_target_geometry(self):
        app = APP.HighSteelApp.__new__(APP.HighSteelApp)
        app.level = 1
        app.auto_x = 720
        app.auto_y = 510 + 1.5 * (APP.TOWER_LAYOUTS[0]["targets"][0] - 510)
        self.assertTrue(app._auto_blocks_target(0))
        app.auto_x = 1000
        self.assertFalse(app._auto_blocks_target(0))

    def test_scheduled_tick_can_be_cancelled(self):
        class FakeRoot:
            def __init__(self):
                self.cancelled = []

            def after_cancel(self, identifier):
                self.cancelled.append(identifier)

        app = APP.HighSteelApp.__new__(APP.HighSteelApp)
        app.root = FakeRoot()
        app.tick_after_id = "timer-1"
        app._cancel_tick()
        self.assertEqual(app.root.cancelled, ["timer-1"])
        self.assertIsNone(app.tick_after_id)


if __name__ == "__main__":
    unittest.main()
