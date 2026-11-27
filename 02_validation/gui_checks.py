"""Run the Tkinter acceptance checks with Python 3.10+: python 02_validation/gui_checks.py."""

import importlib.util
import json
import math
import tempfile
import tkinter as tk
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("high_steel_desktop_gui", ROOT / "04_desktop" / "app.py")
APP = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(APP)


class DesktopGuiChecks(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = tk.Tk()
        self.root.withdraw()
        score_path = Path(self.temp_dir.name) / "high_score.json"
        with patch.object(APP.HighSteelApp, "_high_score_path", return_value=score_path):
            self.app = APP.HighSteelApp(self.root)
        self.root.update_idletasks()

    def tearDown(self):
        self.app._cancel_tick()
        if self.app.level_after_id is not None:
            self.root.after_cancel(self.app.level_after_id)
        self.root.destroy()
        self.temp_dir.cleanup()

    def test_scene_header_controls_and_mirrored_crane(self):
        self.assertEqual(self.app.scene_width, self.app.background_images[0].width())
        self.assertEqual(self.app.scene_height, self.app.background_images[0].height())
        timer_parent = self.app.stat_values["timer"].master
        self.assertEqual(timer_parent.winfo_parent(), self.app.start_button.master.winfo_parent())
        self.assertEqual(timer_parent.pack_info()["side"], "left")
        self.assertEqual(int(self.app.graph.cget("height")), 112)
        self.assertTrue(self.app.scene.find_withtag("player-crane"))
        self.app.orientation = -1
        self.app.trolley_x = 465
        self.app._draw_scene()
        self.assertAlmostEqual(self.app._screen_trolley_x(), 155)
        self.assertTrue(self.app.scene.find_withtag("player-crane"))
        self.app._key_down(SimpleNamespace(keysym="Left"))
        self.assertIn("left", self.app.keys)
        self.app._key_up(SimpleNamespace(keysym="Left"))
        self.assertNotIn("left", self.app.keys)

    def test_graph_marks_light_beam_weight_and_ignores_cable_sway(self):
        self.app.start_game()
        self.app.carried = 0
        self.app.beams[0]["weight"] = 3250

        def marker_center():
            markers = [item for item in self.app.graph.find_all()
                       if self.app.graph.type(item) == "oval"
                       and self.app.graph.itemcget(item, "fill") == "#ffd987"]
            self.assertEqual(len(markers), 1)
            x1, y1, x2, y2 = self.app.graph.coords(markers[0])
            return (x1 + x2) / 2, (y1 + y2) / 2

        self.app._draw_graph()
        marker_before = marker_center()
        self.assertAlmostEqual(marker_before[1], 83 - 3250 / 20000 * 75)
        with patch.object(self.app, "_sway_x", return_value=100):
            self.app._draw_graph()
            self.assertEqual(marker_center(), marker_before)

    def test_pause_freezes_timer_and_controls_save_button(self):
        self.app.start_game()
        self.app.remaining = 60.0
        self.app.toggle_pause()
        self.assertTrue(self.app.paused)
        self.assertEqual(str(self.app.save_button.cget("state")), "normal")
        self.assertIsNone(self.app.tick_after_id)
        self.app.last_tick -= 10
        self.app._tick()
        self.assertEqual(self.app.remaining, 60.0)
        self.app.toggle_pause()
        self.assertFalse(self.app.paused)
        self.assertEqual(str(self.app.save_button.cget("state")), "disabled")
        self.assertGreater(self.app.remaining, 59.9)

    def test_final_seconds_and_capacity_warning_flash(self):
        self.app.start_game()
        self.app.remaining = 10
        self.app.trolley_x = APP.MAST_PIVOT + 112 * 500 / 150
        self.app.carried = 0
        self.app.beams[0]["weight"] = 7236
        with patch.object(APP.time, "monotonic", return_value=100.0):
            self.app._update_hud()
        self.assertEqual(self.app.stat_values["timer"].cget("fg"), "#ff5e59")
        self.assertEqual(self.app.stat_values["capacity"].cget("fg"), "#ff5e59")

    def test_failure_worker_falls_and_bounces(self):
        self.app.start_game()
        self.app._fail("TIME EXPIRED")
        worker_head = self.app.failure_worker_items[0]
        self.assertEqual(len(self.app.failure_worker_items), 5)
        now = APP.time.monotonic()
        self.app.failure_started = now - 0.85
        with patch.object(APP.time, "monotonic", return_value=now):
            self.app._animate_failure()
        first = self.app.scene.coords(worker_head)
        first_y = (first[1] + first[3]) / 2 / self.app.scene_scale
        self.assertAlmostEqual(first_y, 460 - 35 * math.sin(math.pi * 0.10 / 0.25), delta=1)
        self.app.failure_started = now - 1.10
        with patch.object(APP.time, "monotonic", return_value=now):
            self.app._animate_failure()
        second = self.app.scene.coords(worker_head)
        second_y = (second[1] + second[3]) / 2 / self.app.scene_scale
        self.assertGreater(second_y, first_y)
        self.assertLess(second_y, 460)

    def test_checkpoint_file_restores_progress_and_beam_identity(self):
        self.app.level = 3
        self.app._begin_level("Test level")
        self.app.remaining = 47.5
        self.app.score = 410
        self.app.filled_targets = {0}
        self.app.beams[2]["state"] = "placed"
        self.app.beams[2]["target"] = 0
        checkpoint_path = Path(self.temp_dir.name) / "checkpoint.json"
        self.app.toggle_pause()
        with patch.object(APP.filedialog, "asksaveasfilename", return_value=str(checkpoint_path)):
            self.app.save_progress()
        saved = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        self.assertEqual(saved["placements"], [{"target": 0, "beam_id": 3}])
        self.assertNotIn("path", saved)
        other_root = tk.Tk()
        other_root.withdraw()
        try:
            other_score_path = Path(self.temp_dir.name) / "other_high_score.json"
            with patch.object(APP.HighSteelApp, "_high_score_path", return_value=other_score_path):
                other_app = APP.HighSteelApp(other_root)
            with patch.object(APP.filedialog, "askopenfilename", return_value=str(checkpoint_path)):
                other_app.load_progress()
            self.assertEqual(other_app.level, 3)
            self.assertAlmostEqual(other_app.remaining, 47.5, delta=0.1)
            self.assertEqual(other_app.score, 410)
            self.assertEqual(other_app.filled_targets, {0})
            self.assertEqual(other_app.beams[2]["state"], "placed")
            self.assertEqual(other_app.beams[2]["target"], 0)
            self.assertEqual(other_app.orientation, 1)
            self.assertEqual(other_app.trolley_x, APP.TROLLEY_HOME)
            self.assertEqual(other_app.high_score, 410)
        finally:
            if "other_app" in locals():
                other_app._cancel_tick()
            other_root.destroy()

    def test_worker_auto_crane_bird_and_placement_hazards(self):
        self.app.start_game()
        self.app.trolley_x = 746
        self.app.hook_y = 510 + (258 - 510) / 1.3
        self.app.run_elapsed = 0
        self.app._animate_hazards(100, 0)
        self.assertEqual(self.app.score, -10)
        self.app._animate_hazards(100, 0)
        self.assertEqual(self.app.score, -10, "Continuous worker contact should count once")

        self.app.trolley_x = 770
        target_y = 510 + 1.5 * (APP.TOWER_LAYOUTS[0]["targets"][0] - 510)
        self.app.hook_y = 510 + (target_y - 22 - 510) / 1.3
        self.app.run_elapsed = 4
        self.app._animate_hazards(101, 0)
        self.assertEqual(self.app.score, -20)

        self.app.trolley_x = 528
        self.app.hook_y = 333
        self.app.run_elapsed = (588 / 1600) * 14
        self.app.last_bird_cycle = -1
        self.app._animate_hazards(102, 0)
        self.assertEqual(self.app.sway_started, 102)
        self.assertEqual(self.app.last_bird_cycle, 0)

        self.app.auto_placements = 0
        for cycle in (1, 2, 3):
            self.app.run_elapsed = cycle * 8 + 4.8
            self.app._animate_hazards(102 + cycle, 0)
            self.assertEqual(self.app.auto_placements, cycle)

    def test_overload_and_timeout_restart_paths(self):
        self.app.start_game()
        self.app.level = 3
        self.app.score = 420
        self.app.carried = 2
        self.app.beams[2]["weight"] = 5750
        self.app.trolley_x = 810
        self.app._tick()
        self.assertEqual(self.app.failure_cause, "LOAD LIMIT EXCEEDED")
        self.assertEqual(self.app.start_button.cget("text"), "Restart Level")
        self.app._start_action()
        self.assertEqual((self.app.level, self.app.score, self.app.running), (3, 420, True))
        self.app.remaining = 0.001
        self.app.last_tick = APP.time.monotonic() - 0.02
        self.app._tick()
        self.assertEqual(self.app.failure_cause, "TIME EXPIRED")
        self.assertEqual(self.app.start_button.cget("text"), "Restart Game")
        self.app._start_action()
        self.assertEqual((self.app.level, self.app.score, self.app.running), (1, 0, True))

    def test_level_progression_completion_and_high_score(self):
        self.app.start_game()
        layout = APP.TOWER_LAYOUTS[0]
        for target in range(3):
            self.app.carried = target
            self.app.beams[target]["state"] = "carried"
            self.app.trolley_x = layout["centers"][target]
            target_y = 510 + 1.5 * (layout["targets"][target] - 510)
            self.app.hook_y = 510 + (target_y - 6.5 - 510) / 1.3
            self.app.auto_x = 1000
            self.app.auto_y = 120
            self.app.toggle_beam()
            self.assertIn(target, self.app.filled_targets)
        self.assertEqual((self.app.level, self.app.score), (1, 500))
        self.assertIsNotNone(self.app.level_after_id)
        self.root.after_cancel(self.app.level_after_id)
        self.app.level_after_id = None
        self.app._advance_level()
        self.assertTrue(self.app.running)
        self.assertEqual(self.app.level, 2)
        self.assertAlmostEqual(self.app.remaining, APP.LEVEL_SECONDS[1], delta=0.1)
        self.app.level = 5
        self.app.score = 1800
        self.app._complete_level()
        self.assertTrue(self.app.finished)
        self.assertEqual(self.app.score, 2000)
        self.assertEqual(self.app.start_button.cget("text"), "Play Again")
        score_file = Path(self.temp_dir.name) / "high_score.json"
        self.assertEqual(json.loads(score_file.read_text(encoding="utf-8"))["high_score"], 2000)


if __name__ == "__main__":
    unittest.main(verbosity=2)
