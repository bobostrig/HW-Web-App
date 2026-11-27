"""Native Tkinter desktop version of High Steel.

Run from the project root with: python 04_desktop/app.py
The fixed construction-site artwork is rendered from the SVG scene in index.html;
all interactive pieces and the live graph are drawn natively on Tkinter canvases.
"""

from __future__ import annotations

import json
import math
import os
import random
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox


ROOT_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = Path(__file__).resolve().parent / "assets"
SCENE_WIDTH = 1440
SCENE_HEIGHT = 660
MAST_PIVOT = 310
TROLLEY_HOME = 528
LEVEL_SECONDS = (120, 90, 60, 45, 30)
CAPACITY_CHART = ((0, 20000), (50, 20000), (75, 13000), (100, 9000), (125, 7000), (150, 5500))
TOWER_LAYOUTS = (
    {"rows": (458, 376, 294, 261), "targets": (410.5, 328.5, 274.5), "centers": (720, 720, 720), "widths": (144, 144, 144), "heights": (27, 27, 15)},
    {"rows": (458, 382, 300, 261), "targets": (420, 342, 279), "centers": (713, 727, 717), "widths": (132, 126, 118), "heights": (24, 22, 13)},
    {"rows": (458, 398, 318, 261), "targets": (427, 358, 288), "centers": (727, 712, 724), "widths": (118, 108, 98), "heights": (21, 19, 11)},
    {"rows": (458, 385, 335, 261), "targets": (421, 360, 296), "centers": (711, 729, 713), "widths": (104, 92, 82), "heights": (18, 16, 10)},
    {"rows": (458, 400, 325, 261), "targets": (429, 363, 292), "centers": (727, 713, 723), "widths": (90, 78, 66), "heights": (15, 13, 9)},
)
BEAM_SPAWN_RANGES = ((155, 205), (360, 470), (520, 660))
SAVE_VERSION = 1
SCENE_SCALES = (1.0, 0.9, 0.8, 0.7, 0.6)


def capacity_at_radius(radius: float) -> float:
    """Return the interpolated maximum load in pounds for a 0–150 ft radius."""
    radius = min(150.0, max(0.0, float(radius)))
    for (r0, c0), (r1, c1) in zip(CAPACITY_CHART, CAPACITY_CHART[1:]):
        if radius <= r1:
            return c0 + ((radius - r0) / (r1 - r0)) * (c1 - c0)
    return CAPACITY_CHART[-1][1]


def scene_radius(screen_x: float) -> float:
    return min(150.0, abs(float(screen_x) - MAST_PIVOT) * 150.0 / 500.0)


def player_scene_y(local_y: float) -> float:
    return 510 + 1.3 * (local_y - 510)


def auto_scene_y(local_y: float) -> float:
    return 510 + 1.45 * (local_y - 510)


def make_checkpoint(level: int, remaining: float, score: int, placed_targets: set[int]) -> dict:
    return {
        "format": "high-steel-checkpoint",
        "version": SAVE_VERSION,
        "level": level,
        "remaining_seconds": round(remaining, 2),
        "score": score,
        "placed_targets": sorted(placed_targets),
    }


def validate_checkpoint(data: object) -> tuple[int, float, int, set[int]]:
    if not isinstance(data, dict) or data.get("format") != "high-steel-checkpoint" or data.get("version") != SAVE_VERSION:
        raise ValueError("This save is not a supported High Steel checkpoint.")
    level = data.get("level")
    score = data.get("score")
    remaining = data.get("remaining_seconds")
    targets = data.get("placed_targets")
    if not isinstance(level, int) or isinstance(level, bool) or not 1 <= level <= 5:
        raise ValueError("The saved level is invalid.")
    if not isinstance(score, int) or isinstance(score, bool):
        raise ValueError("The saved score is invalid.")
    if not isinstance(remaining, (int, float)) or isinstance(remaining, bool) or not 0 <= remaining <= LEVEL_SECONDS[level - 1] or not math.isfinite(remaining):
        raise ValueError("The saved timer is invalid.")
    if not isinstance(targets, list) or any(not isinstance(i, int) or isinstance(i, bool) or i not in (0, 1, 2) for i in targets) or len(set(targets)) != len(targets):
        raise ValueError("The saved target list is invalid.")
    return level, float(remaining), score, set(targets)


class HighSteelApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("High Steel | Tower Crane Challenge")
        self.root.configure(bg="#08131d")
        available_width = root.winfo_screenwidth() - 32
        available_height = root.winfo_screenheight() - 72
        self.scene_scale = next((scale for scale in SCENE_SCALES
                                 if SCENE_WIDTH * scale + 32 <= available_width
                                 and SCENE_HEIGHT * scale + 215 <= available_height), 0.6)
        self.scene_width = round(SCENE_WIDTH * self.scene_scale)
        self.scene_height = round(SCENE_HEIGHT * self.scene_scale)
        window_width = min(available_width, max(900, self.scene_width + 32))
        window_height = min(available_height, self.scene_height + 215)
        self.root.geometry(f"{window_width}x{window_height}")
        self.root.minsize(window_width, window_height)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

        self.high_score_path = self._high_score_path()
        self.high_score = self._load_high_score()
        self.record_until = 0.0
        self.score = 0
        self.level = 1
        self.remaining = float(LEVEL_SECONDS[0])
        self.running = False
        self.paused = False
        self.failed = False
        self.finished = False
        self.started = False
        self.failure_cause = ""
        self.run_elapsed = 0.0
        self.last_tick = time.monotonic()
        self.last_draw = self.last_tick
        self.keys: set[str] = set()
        self.trolley_x = float(TROLLEY_HOME)
        self.hook_y = 333.0
        self.orientation = 1
        self.turn_started = 0.0
        self.pause_started = 0.0
        self.turn_from = 1
        self.turn_to = 1
        self.carried: int | None = None
        self.beams: list[dict] = []
        self.filled_targets: set[int] = set()
        self.penalty_message = ""
        self.penalty_until = 0.0
        self.last_worker_contact = False
        self.last_auto_contact = False
        self.sway_started = -100.0
        self.sway_direction = 1
        self.last_bird_cycle = -1
        self.worker_x_offset = 0.0
        self.auto_x = 922.0
        self.auto_y = 120.0
        self.auto_placements = 0
        self.auto_cycle_seen = -1
        self.message = "Press Start Game to begin."

        self._build_ui()
        self._bind_inputs()
        self._spawn_beams()
        self._update_hud()
        self._draw_scene()
        self._draw_graph()
        self._draw_start_overlay()

    @staticmethod
    def _high_score_path() -> Path:
        base = os.environ.get("LOCALAPPDATA")
        folder = Path(base) / "HighSteel" if base else Path.home() / ".high_steel"
        return folder / "high_score.json"

    def _load_high_score(self) -> int:
        try:
            saved = json.loads(self.high_score_path.read_text(encoding="utf-8"))
            value = saved.get("high_score", 0)
            return value if isinstance(value, int) and value > 0 else 0
        except (OSError, ValueError, AttributeError):
            return 0

    def _persist_high_score(self) -> None:
        try:
            self.high_score_path.parent.mkdir(parents=True, exist_ok=True)
            self.high_score_path.write_text(json.dumps({"high_score": self.high_score}), encoding="utf-8")
        except OSError:
            self._set_message("Could not save the local high score; it remains for this session.")

    def _build_ui(self) -> None:
        header = tk.Frame(self.root, bg="#08131d")
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(6, 4))
        title_box = tk.Frame(header, bg="#08131d")
        title_box.pack(side="left")
        tk.Label(title_box, text="HIGH STEEL · CRANE CHALLENGE", fg="#77d9df", bg="#08131d",
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        tk.Label(title_box, text="Build above the skyline", fg="#edf4f6", bg="#08131d",
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        actions = tk.Frame(header, bg="#08131d")
        actions.pack(side="right", anchor="e")
        self.start_button = self._button(actions, "Start Game", self._start_action, "#f1bd68", "#19252c")
        self.start_button.pack(side="left", padx=3)
        self.pause_button = self._button(actions, "Pause", self.toggle_pause)
        self.pause_button.pack(side="left", padx=3)
        self.pause_button.configure(state="disabled")
        self.save_button = self._button(actions, "Save Progress", self.save_progress)
        self.save_button.pack(side="left", padx=3)
        self.save_button.configure(state="disabled")
        self.load_button = self._button(actions, "Load Save…", self.load_progress)
        self.load_button.pack(side="left", padx=3)

        scene_border = tk.Frame(self.root, bg="#263a45", padx=1, pady=1)
        scene_border.grid(row=1, column=0, sticky="nsew", padx=12)
        scene_border.grid_rowconfigure(0, weight=1)
        scene_border.grid_columnconfigure(0, weight=1)
        self.scene = tk.Canvas(scene_border, width=self.scene_width, height=self.scene_height,
                               bg="#7393a0", highlightthickness=0)
        self.scene.grid(row=0, column=0, sticky="nsew")
        percent = round(self.scene_scale * 100)
        self.background_images = [tk.PhotoImage(file=str(ASSET_DIR / f"scene-level-{level}-{percent}.png")) for level in range(1, 6)]
        self.background_item = self.scene.create_image(0, 0, image=self.background_images[0], anchor="nw", tags=("background",))
        self.scene.create_rectangle(0, 0, self.scene_width, self.scene_height, outline="#344b56", width=1, tags=("frame",))

        footer = tk.Frame(self.root, bg="#0b1722")
        footer.grid(row=2, column=0, sticky="ew", padx=12, pady=(4, 2))
        stats = tk.Frame(footer, bg="#0b1722")
        stats.pack(side="left", fill="x", expand=True)
        for column in range(4):
            stats.grid_columnconfigure(column, weight=1)
        self.stat_values: dict[str, tk.Label] = {}
        for index, (key, label) in enumerate((("timer", "TIME LEFT"), ("score", "SCORE"), ("high", "HIGH SCORE"),
                           ("level", "LEVEL"), ("radius", "RADIUS"), ("capacity", "LOAD / CAPACITY"),
                           ("beams", "TO PLACE"))):
            card = tk.Frame(stats, bg="#142631", highlightbackground="#344953", highlightthickness=1)
            card.grid(row=index // 4, column=index % 4, sticky="ew", padx=(0, 3), pady=(0, 3))
            tk.Label(card, text=label, fg="#9babb5", bg="#142631", font=("Segoe UI", 7, "bold")).pack(anchor="w", padx=5, pady=(2, 0))
            value = tk.Label(card, text="—", fg="#f5fafb", bg="#142631", font=("Segoe UI", 10, "bold"))
            value.pack(anchor="w", padx=5, pady=(0, 2))
            self.stat_values[key] = value

        graph_wrap = tk.Frame(footer, bg="#142631", highlightbackground="#344953", highlightthickness=1)
        graph_wrap.pack(side="right", padx=(8, 0))
        graph_head = tk.Frame(graph_wrap, bg="#142631")
        graph_head.pack(fill="x", padx=8, pady=(2, 0))
        tk.Label(graph_head, text="CAPACITY CURVE", fg="#dce8eb", bg="#142631",
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        self.graph_note = tk.Label(graph_head, text="No beam carried", fg="#9babb5", bg="#142631",
                                   font=("Segoe UI", 8))
        self.graph_note.pack(side="right")
        self.graph = tk.Canvas(graph_wrap, width=340, height=112, bg="#101e29", highlightthickness=0)
        self.graph.pack(padx=7, pady=(2, 3))

        self.status_var = tk.StringVar(value=self.message)
        tk.Label(self.root, textvariable=self.status_var, anchor="w", fg="#9babb5", bg="#08131d",
                 font=("Segoe UI", 8)).grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 3))

    @staticmethod
    def _button(parent: tk.Widget, text: str, command, bg: str = "#182c37", fg: str = "#edf4f6") -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, activebackground="#35515e",
                         activeforeground="#ffffff", relief="flat", padx=12, pady=7,
                         font=("Segoe UI", 9, "bold"), cursor="hand2")

    def _bind_inputs(self) -> None:
        self.root.bind_all("<KeyPress>", self._key_down)
        self.root.bind_all("<KeyRelease>", self._key_up)
        self.root.bind("<FocusOut>", lambda _event: self.keys.clear())

    def _key_down(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key in ("left", "right", "up", "down", "a", "d", "w", "s"):
            self.keys.add(key)
            return "break"
        if key == "space" and not self.paused and self.running and not self.failed:
            self.toggle_beam()
            return "break"
        if key == "escape" and self.running:
            self.toggle_pause()

    def _key_up(self, event: tk.Event) -> None:
        self.keys.discard(event.keysym.lower())

    def _set_message(self, message: str) -> None:
        self.message = message
        self.status_var.set(message)

    def _spawn_beams(self) -> None:
        layout = TOWER_LAYOUTS[self.level - 1]
        self.beams = []
        for beam_id, (minimum, maximum) in enumerate(BEAM_SPAWN_RANGES, start=1):
            x = random.randrange(minimum // 5, maximum // 5 + 1) * 5
            if beam_id == 1:
                weight = 3250 + 500 * (self.level - 1) + random.choice((0, 250))
            elif beam_id == 2:
                weight = 4250 + 500 * (self.level - 1) + random.choice((0, 250))
            else:
                weight = 5750 + 250 * (self.level - 1)
            target_x = layout["centers"][beam_id - 1]
            route_cap = capacity_at_radius(max(scene_radius(x), scene_radius(target_x)))
            if beam_id != 3:
                weight = min(weight, int(route_cap) - 100)
            self.beams.append({"id": beam_id, "x": float(x), "weight": int(weight), "state": "ground"})
        self.carried = None
        self.filled_targets.clear()

    def start_game(self) -> None:
        self.score = 0
        self.level = 1
        self.started = True
        self._begin_level("Level 1 started. Place all three beams before time runs out.")

    def _start_action(self) -> None:
        if self.failed and self.failure_cause != "TIME EXPIRED":
            self.started = True
            self._begin_level(f"Level {self.level} restarted. Try the lift again.")
        else:
            self.start_game()

    def _begin_level(self, message: str, preserved_targets: set[int] | None = None) -> None:
        self.failed = False
        self.finished = False
        self.running = True
        self.paused = False
        self.remaining = min(float(LEVEL_SECONDS[self.level - 1]), max(0.0, self.remaining)) if preserved_targets is not None else float(LEVEL_SECONDS[self.level - 1])
        self.trolley_x = float(TROLLEY_HOME)
        self.hook_y = 333.0
        self.orientation = 1
        self.turn_started = 0.0
        self.pause_started = 0.0
        self.carried = None
        self.filled_targets = set(preserved_targets or ())
        self.keys.clear()
        self.run_elapsed = 0.0
        self.scene.delete("collapse")
        self.scene.delete("collapse-worker")
        self.worker_x_offset = 0.0
        self.auto_x, self.auto_y = 1000.0, 120.0
        self.auto_placements = 0
        self.auto_cycle_seen = -1
        self.sway_started = -100.0
        self.last_bird_cycle = -1
        self.last_worker_contact = False
        self.last_auto_contact = False
        self._spawn_beams()
        self.filled_targets = set(preserved_targets or ())
        for index in self.filled_targets:
            if index < len(self.beams):
                self.beams[index]["state"] = "placed"
                self.beams[index]["target"] = index
        self.pause_button.configure(state="normal", text="Pause")
        self.save_button.configure(state="disabled")
        self.start_button.configure(text="Restart Game", state="normal")
        self.last_tick = time.monotonic()
        self.scene.delete("overlay")
        self.scene.itemconfigure(self.background_item, image=self.background_images[self.level - 1])
        self._set_message(message)
        self._update_hud()
        self._draw_scene()
        self._draw_graph()
        self._tick()

    def toggle_pause(self) -> None:
        if not self.running or self.failed or self.finished:
            return
        self.paused = not self.paused
        self.keys.clear()
        self.pause_button.configure(text="Resume" if self.paused else "Pause")
        self.save_button.configure(state="normal" if self.paused else "disabled")
        if self.paused:
            self.pause_started = time.monotonic()
            self._set_message("Paused. Save Progress to create a portable level checkpoint.")
            self._draw_pause_overlay()
        else:
            now = time.monotonic()
            paused_for = now - self.pause_started if self.pause_started else 0.0
            self.last_tick = now
            if self.turn_started:
                self.turn_started += paused_for
            if self.sway_started > -100:
                self.sway_started += paused_for
            if self.penalty_until:
                self.penalty_until += paused_for
            self.pause_started = 0.0
            self._set_message("Game resumed.")
            self.scene.delete("overlay")
            self._tick()

    def save_progress(self) -> None:
        if not self.paused:
            self._set_message("Pause the game before saving progress.")
            return
        path = filedialog.asksaveasfilename(title="Save High Steel progress", defaultextension=".json",
                                            filetypes=(("High Steel save", "*.json"), ("All files", "*.*")))
        if not path:
            return
        data = make_checkpoint(self.level, self.remaining, self.score, self.filled_targets)
        try:
            Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Could not save progress", str(error), parent=self.root)
            return
        self._set_message(f"Progress saved to {Path(path).name}. Move this file to the other computer to continue.")

    def load_progress(self) -> None:
        path = filedialog.askopenfilename(title="Load High Steel progress",
                                          filetypes=(("High Steel save", "*.json"), ("All files", "*.*")))
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            level, remaining, score, targets = validate_checkpoint(data)
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
            messagebox.showerror("Could not load progress", str(error), parent=self.root)
            return
        self.level, self.score, self.remaining = level, score, remaining
        self._begin_level(f"Level {level} checkpoint loaded. Remaining beams were regenerated.", targets)

    def toggle_beam(self) -> None:
        if self.carried is not None:
            beam = self.beams[self.carried]
            target_index = self._target_under_load()
            if target_index is not None and target_index not in self.filled_targets:
                beam["state"] = "placed"
                beam["target"] = target_index
                self.filled_targets.add(target_index)
                self.score += 100
                self._update_record()
                self._set_message(f"Beam {beam['id']} placed. +100 points.")
                self.carried = None
                if len(self.filled_targets) == 3:
                    self._complete_level()
            else:
                beam["state"] = "ground"
                beam["x"] = self._load_x()
                self.carried = None
                self._set_message("Beam set down. Align it with an unfilled target to place it.")
        else:
            if self.hook_screen_y() < 430:
                self._set_message("Lower the hook close to a beam to pick it up.")
                return
            target_x = self._load_x()
            found = next((i for i, beam in enumerate(self.beams)
                          if beam["state"] == "ground" and abs(beam["x"] - target_x) <= 42), None)
            if found is None:
                self._set_message("Move the hook over a beam and press Space to pick it up.")
                return
            self.carried = found
            self.beams[found]["state"] = "carried"
            self._set_message(f"Carrying beam {self.beams[found]['id']} · {self.beams[found]['weight']:,} lb.")
        self._update_hud()
        self._draw_scene()
        self._draw_graph()

    def _target_under_load(self) -> int | None:
        layout = TOWER_LAYOUTS[self.level - 1]
        x = self._load_x()
        y = self.hook_screen_y() + 7
        for index in range(3):
            target_y = 510 + 1.5 * (layout["targets"][index] - 510)
            if index not in self.filled_targets and abs(x - layout["centers"][index]) <= layout["widths"][index] / 2 and abs(y - target_y) < 25:
                if abs(self.auto_x - layout["centers"][index]) < 95 and abs(self.auto_y - target_y) < 24:
                    return None
                return index
        return None

    def hook_screen_y(self) -> float:
        return player_scene_y(self.hook_y)

    def _load_x(self) -> float:
        return MAST_PIVOT + (self.trolley_x - MAST_PIVOT) * self.orientation + self._sway_x()

    def _sway_x(self) -> float:
        elapsed = time.monotonic() - self.sway_started
        if not 0 <= elapsed <= 5.5:
            return 0.0
        return self.sway_direction * 112 * math.exp(-0.48 * elapsed) * math.sin(8.2 * elapsed)

    def _tick(self) -> None:
        if not self.running or self.paused or self.failed or self.finished:
            return
        now = time.monotonic()
        dt = min(now - self.last_tick, 0.05)
        self.last_tick = now
        self.remaining = max(0.0, self.remaining - dt)
        if self.remaining <= 0:
            self._fail("TIME EXPIRED")
            return
        horizontal = (-1 if "left" in self.keys or "a" in self.keys else 0) + (1 if "right" in self.keys or "d" in self.keys else 0)
        vertical = (-1 if "up" in self.keys or "w" in self.keys else 0) + (1 if "down" in self.keys or "s" in self.keys else 0)
        if self.turn_started:
            progress = min(1.0, (now - self.turn_started) / 1.6)
            if progress >= 1:
                self.orientation = self.turn_to
                self.turn_started = 0.0
        elif horizontal:
            should_turn = (self.orientation == 1 and horizontal < 0 and self.trolley_x <= MAST_PIVOT) or (self.orientation == -1 and horizontal > 0 and self.trolley_x <= MAST_PIVOT)
            if should_turn:
                self.turn_from, self.turn_to, self.turn_started = self.orientation, -self.orientation, now
                self._set_message("Crane is turning to the other side…")
            else:
                direction = horizontal * self.orientation
                maximum = 810 if self.orientation == 1 else 620
                self.trolley_x = max(MAST_PIVOT, min(maximum, self.trolley_x + direction * 125 * dt))
        if vertical:
            self.hook_y = max(175.0, min(490.0, self.hook_y + vertical * 115 * dt))
        self._animate_hazards(now, dt)
        radius = self.trolley_radius()
        if self.carried is not None and self.beams[self.carried]["weight"] >= capacity_at_radius(radius):
            self._fail("LOAD LIMIT EXCEEDED")
            return
        if now - self.last_draw >= 0.045:
            self._draw_scene()
            self._draw_graph()
            self._update_hud()
            self.last_draw = now
        self.root.after(16, self._tick)

    def _animate_hazards(self, now: float, dt: float) -> None:
        self.run_elapsed += dt
        elapsed = self.run_elapsed
        self.worker_x_offset = math.sin(elapsed * 0.55) * 48
        phase = (elapsed % 8.0) / 8.0
        cycle = int(elapsed // 8.0)
        if cycle != self.auto_cycle_seen:
            self.auto_cycle_seen = cycle
        self.auto_x = 885 + 115 * math.cos(phase * math.tau)
        layout = TOWER_LAYOUTS[self.level - 1]
        target_y = 510 + 1.5 * (layout["targets"][min(self.auto_placements, 2)] - 510)
        approach = max(0.0, min(1.0, (1000 - self.auto_x) / 230))
        eased = approach * approach * (3 - 2 * approach)
        self.auto_y = 120 + (target_y - 120) * eased
        bird_duration = 14.0
        bird_cycle = int(elapsed // bird_duration)
        self.bird_x = -80 + (elapsed % bird_duration) / bird_duration * 1600
        self.bird_y = (140, 170, 200, 230, 260, 275)[bird_cycle % 6]
        cable_top = 1.3 * 175 - 153
        if bird_cycle != self.last_bird_cycle and abs(self.bird_x + 20 - self._load_x()) < 22 and cable_top <= self.bird_y <= self.hook_screen_y():
            self.last_bird_cycle = bird_cycle
            self.sway_started = now
            self.sway_direction = random.choice((-1, 1))
            self._set_message("A bird struck the cable. The hook and load are swinging.")
        if phase >= 0.54 and self.auto_placements < 3 and cycle > self.auto_placements:
            self.auto_placements += 1
        player_x = self._load_x()
        contact_y = self.hook_screen_y() + (7 if self.carried is not None else 22)
        worker_x = 746 + self.worker_x_offset
        worker_hit = abs(player_x - worker_x) < (39 if self.carried is not None else 24) and abs(contact_y - 280) < 36
        if worker_hit and not self.last_worker_contact:
            self._penalty("Your hook or beam hit the worker.")
        self.last_worker_contact = worker_hit
        auto_hit = abs(player_x - self.auto_x) < (82 if self.carried is not None else 54) and abs(contact_y - self.auto_y) < 22
        if auto_hit and not self.last_auto_contact:
            self._penalty("Your hook or beam hit the automatic crane's load.")
        self.last_auto_contact = auto_hit

    def _penalty(self, message: str) -> None:
        self.score -= 10
        self.penalty_message = "-10"
        self.penalty_until = time.monotonic() + 1.1
        self._set_message(f"{message} -10 points.")
        self._update_record()

    def _update_record(self) -> None:
        if self.score > self.high_score:
            self.high_score = self.score
            self.record_until = time.monotonic() + 1.2
            self._persist_high_score()

    def _complete_level(self) -> None:
        self.running = False
        self.score += 200
        self._update_record()
        if self.level >= 5:
            self.finished = True
            self._set_message(f"All five levels complete. Final score: {self.score:,}.")
            self.start_button.configure(text="Play Again")
            self.scene.delete("overlay")
            self.scene.create_rectangle(0, 0, SCENE_WIDTH, SCENE_HEIGHT, fill="#08131d", stipple="gray50", outline="", tags=("overlay",))
            self.scene.create_text(720, 285, text="CONSTRUCTION FINISHED", fill="#ffd987", font=("Segoe UI", 19, "bold"), tags=("overlay",))
            self.scene.create_text(720, 340, text="GAME COMPLETE", fill="#fff6e7", font=("Segoe UI", 36, "bold"), tags=("overlay",))
            self.scene.create_text(720, 385, text=f"Final score: {self.score:,}", fill="#d2dfe4", font=("Segoe UI", 17), tags=("overlay",))
            self._scale_scene_items("overlay")
        else:
            self._set_message(f"Level {self.level} complete. +200 bonus. Starting level {self.level + 1}.")
            self.level += 1
            self.remaining = float(LEVEL_SECONDS[self.level - 1])
            self.root.after(900, lambda: self._begin_level(f"Level {self.level} started with a new tower layout."))

    def _fail(self, cause: str) -> None:
        self.running = False
        self.failed = True
        self.failure_cause = cause
        self.pause_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self._set_message("Time expired. The crane and tower are collapsing." if cause == "TIME EXPIRED" else "Load limit exceeded. The crane and tower are collapsing.")
        self.scene.delete("dynamic")
        self.scene.delete("overlay")
        self.scene.create_rectangle(0, 0, SCENE_WIDTH, SCENE_HEIGHT, fill="#08131d", stipple="gray50", outline="", tags=("overlay",))
        pieces = []
        for x in (625, 815):
            pieces.append((self.scene.create_line(x, 137, x, 465, fill="#71838a", width=10, tags="collapse"), x, 137, x, 465))
        for y in (213, 336, 432):
            pieces.append((self.scene.create_line(617, y, 823, y, fill="#9aa6a6", width=8, tags="collapse"), 617, y, 823, y))
        for x1, y1, x2, y2 in ((286, 47, 286, 510), (334, 47, 334, 510), (221, 50, 817, 50), (221, 69, 810, 69)):
            pieces.append((self.scene.create_line(x1, y1, x2, y2, fill="#d0a257", width=7, tags="collapse"), x1, y1, x2, y2))
        velocities = [(random.uniform(-65, 65), random.uniform(-20, 20)) for _ in pieces]
        worker_items = self._create_failure_worker()
        self.failure_started = time.monotonic()
        self.failure_pieces = pieces
        self.failure_velocities = velocities
        self.failure_worker_items = worker_items
        self.failure_cause = cause
        self.start_button.configure(text="Restart Game" if cause == "TIME EXPIRED" else "Restart Level")
        self._scale_scene_items("overlay")
        self._scale_scene_items("collapse")
        self._scale_scene_items("collapse-worker")
        self._animate_failure()

    def _create_failure_worker(self) -> list[int]:
        x, y = 746, 280
        return [
            self.scene.create_oval(x - 7, y - 7, x + 7, y + 7, fill="#bd8565", outline="#644c43", width=2, tags="collapse-worker"),
            self.scene.create_polygon(x - 8, y - 4, x + 8, y - 4, x + 5, y - 10, x - 5, y - 10, fill="#f2bd54", outline="#805b2b", width=2, tags="collapse-worker"),
            self.scene.create_polygon(x - 8, y + 8, x + 7, y + 8, x + 12, y + 29, x - 12, y + 29, fill="#c7463b", outline="#792f2b", width=2, tags="collapse-worker"),
            self.scene.create_line(x - 6, y + 27, x - 11, y + 45, fill="#35444a", width=4, tags="collapse-worker"),
            self.scene.create_line(x + 2, y + 27, x + 11, y + 44, fill="#35444a", width=4, tags="collapse-worker"),
        ]

    def _animate_failure(self) -> None:
        if not self.failed:
            return
        elapsed = time.monotonic() - self.failure_started
        for (item, x1, y1, x2, y2), (vx, vy) in zip(self.failure_pieces, self.failure_velocities):
            dx = vx * elapsed
            dy = vy * elapsed + 95 * elapsed * elapsed
            self.scene.coords(item, *((value * self.scene_scale) for value in (x1 + dx, y1 + dy, x2 + dx, y2 + dy)))
        if elapsed < 0.75:
            worker_y = 280 + 180 * (elapsed / 0.75) ** 2
        elif elapsed < 1.0:
            worker_y = 460 - 35 * math.sin(math.pi * (elapsed - 0.75) / 0.25)
        elif elapsed < 1.22:
            worker_y = 460 - 16 * math.sin(math.pi * (elapsed - 1.0) / 0.22)
        else:
            worker_y = 460
        x, y = 746 + min(35, elapsed * 35), worker_y
        coordinates = (
            (x - 7, y - 7, x + 7, y + 7),
            (x - 8, y - 4, x + 8, y - 4, x + 5, y - 10, x - 5, y - 10),
            (x - 8, y + 8, x + 7, y + 8, x + 12, y + 29, x - 12, y + 29),
            (x - 6, y + 27, x - 11, y + 45),
            (x + 2, y + 27, x + 11, y + 44),
        )
        for item, coords in zip(self.failure_worker_items, coordinates):
            self.scene.coords(item, *((value * self.scene_scale) for value in coords))
        if elapsed < 1.85:
            self.root.after(33, self._animate_failure)
        else:
            self.scene.create_text(720, 285, text=self.failure_cause, fill="#ff766d", font=("Segoe UI", 19, "bold"), tags=("overlay", "failure-title"))
            self.scene.create_text(720, 335, text="LEVEL FAILED", fill="#fff6e7", font=("Segoe UI", 34, "bold"), tags=("overlay", "failure-title"))
            self._scale_scene_items("failure-title")

    def _scale_scene_items(self, tag: str) -> None:
        self.scene.scale(tag, 0, 0, self.scene_scale, self.scene_scale)

    def _draw_pause_overlay(self) -> None:
        self.scene.delete("overlay")
        self.scene.create_rectangle(0, 0, SCENE_WIDTH, SCENE_HEIGHT, fill="#08131d", stipple="gray50", outline="", tags=("overlay",))
        self.scene.create_text(720, 300, text="PAUSED", fill="#fff6e7", font=("Segoe UI", 42, "bold"), tags=("overlay",))
        self._scale_scene_items("overlay")

    def _draw_start_overlay(self) -> None:
        self.scene.delete("overlay")
        self.scene.create_rectangle(0, 0, SCENE_WIDTH, SCENE_HEIGHT, fill="#071119", stipple="gray50", outline="", tags=("overlay",))
        self.scene.create_text(720, 270, text="HIGH STEEL", fill="#fff6e7", font=("Segoe UI", 42, "bold"), tags=("overlay",))
        self.scene.create_text(720, 325, text="Place three steel beams on each level. Keep every lift within capacity.",
                               fill="#d2dfe4", font=("Segoe UI", 15), tags=("overlay",))
        self.scene.create_text(720, 365, text="Arrow keys or WASD move · Space picks up or releases · Pause to save a checkpoint",
                               fill="#d2dfe4", font=("Segoe UI", 11), tags=("overlay",))
        self._scale_scene_items("overlay")

    def _draw_scene(self) -> None:
        self.scene.delete("dynamic")
        self._draw_targets()
        # Player trolley and hoist: same geometry and warm steel colors as index.html.
        x = self._load_x()
        trolley_x = self._screen_trolley_x()
        self.scene.create_line(trolley_x, player_scene_y(175), x, self.hook_screen_y(), fill="#273943", width=3, tags="dynamic")
        self.scene.create_rectangle(trolley_x - 21, player_scene_y(147), trolley_x + 21, player_scene_y(175), fill="#efbd66", outline="#725834", width=3, tags="dynamic")
        self.scene.create_rectangle(trolley_x - 16, player_scene_y(153), trolley_x + 16, player_scene_y(158), fill="#ffe1a0", outline="", tags="dynamic")
        for wheel_x in (trolley_x - 13, trolley_x + 13):
            self.scene.create_oval(wheel_x - 4, player_scene_y(172), wheel_x + 4, player_scene_y(182), fill="#705c3b", outline="", tags="dynamic")
        self.scene.create_oval(trolley_x - 5, player_scene_y(163), trolley_x + 5, player_scene_y(173), fill="#ffdf91", outline="", tags="dynamic")
        hy = self.hook_screen_y()
        self.scene.create_rectangle(x - 9, hy - 2, x + 9, hy + 22, fill="#a8b2ae", outline="#394951", width=2, tags="dynamic")
        self.scene.create_rectangle(x - 12, hy + 24, x + 12, hy + 40, fill="#56686e", outline="#394951", width=1, tags="dynamic")

        for index, beam in enumerate(self.beams):
            if beam["state"] == "ground":
                self._draw_beam(beam["x"], 465, beam["weight"], f"beam-{index}")
            elif beam["state"] == "placed":
                layout = TOWER_LAYOUTS[self.level - 1]
                target = beam.get("target", index)
                center = layout["centers"][target]
                y = 510 + 1.5 * (layout["targets"][target] - 510)
                self._draw_placed_beam(center, y, f"placed-{index}")
        if self.carried is not None:
            self._draw_beam(x, hy, self.beams[self.carried]["weight"], "carried")

        self._draw_worker()
        self._draw_automatic_crane()
        self._draw_bird()
        if self.penalty_until > time.monotonic():
            self.scene.create_text(720, 245, text=self.penalty_message, fill="#ff3434",
                                   font=("Segoe UI", 54, "bold"), tags="dynamic")
        if self.paused:
            self._draw_pause_overlay()
        self._scale_scene_items("dynamic")

    def _screen_trolley_x(self) -> float:
        return MAST_PIVOT + (self.trolley_x - MAST_PIVOT) * self.orientation

    def trolley_radius(self) -> float:
        return scene_radius(self._screen_trolley_x())

    def _draw_beam(self, x: float, top: float, weight: int, tag: str) -> None:
        if tag.startswith("beam-"):
            self.scene.create_line(x, 481, x, 499, fill="#293b43", width=3, tags=("dynamic", tag))
            self.scene.create_line(x - 12, 499, x + 12, 499, fill="#293b43", width=3, tags=("dynamic", tag))
        self.scene.create_rectangle(x - 32, top, x + 33, top + 13, fill="#9ba8a7", outline="#33464e", width=2, tags=("dynamic", tag))
        self.scene.create_line(x - 21, top, x - 21, top + 13, fill="#4c616a", width=2, tags=("dynamic", tag))
        self.scene.create_line(x + 21, top, x + 21, top + 13, fill="#4c616a", width=2, tags=("dynamic", tag))
        self.scene.create_rectangle(x - 42, top - 25, x + 42, top - 2, fill="#14252e", outline="#61747a", width=1, tags=("dynamic", tag))
        self.scene.create_text(x, top - 13, text=f"{weight:,} lb", fill="#e9f0eb", font=("Segoe UI", 9, "bold"), tags=("dynamic", tag))

    def _draw_placed_beam(self, x: float, y: float, tag: str) -> None:
        self.scene.create_rectangle(x - 39, y - 7, x + 39, y + 7, fill="#9ba8a7", outline="#33464e", width=2, tags=("dynamic", tag))

    def _draw_targets(self) -> None:
        layout = TOWER_LAYOUTS[self.level - 1]
        for row in layout["rows"]:
            bolt_y = 510 + 1.5 * (row - 510)
            for bolt_x in (625, 815):
                self.scene.create_oval(bolt_x - 3, bolt_y - 3, bolt_x + 3, bolt_y + 3,
                                       fill="#d8c69a", outline="#495c64", width=1, tags="dynamic")
        for index in range(3):
            x = layout["centers"][index]
            y = 510 + 1.5 * (layout["targets"][index] - 510)
            width = layout["widths"][index]
            height = layout["heights"][index] * 1.5
            if index in self.filled_targets:
                color, dash, stroke = "#79d7ac", "", 4
            elif self.carried is not None and self._target_under_load() == index:
                color, dash, stroke = "#ffe19b", "", 5
            else:
                color, dash, stroke = "#77d9df", "7 6", 3
            self.scene.create_rectangle(x - width / 2, y - height / 2, x + width / 2, y + height / 2,
                                        outline=color, width=stroke, dash=dash, tags="dynamic")
            self.scene.create_text(x, y + 4, text=f"TARGET 0{index + 1}", fill="#d5f7f4",
                                   font=("Segoe UI", 10, "bold"), tags="dynamic")

    def _draw_worker(self) -> None:
        x = 746 + self.worker_x_offset
        y = 247.5 + abs(math.sin(self.run_elapsed * 3.4)) * 2
        self.scene.create_line(x - 6, y + 36, x - 11, y + 61, fill="#35444a", width=4, tags="dynamic")
        self.scene.create_line(x + 2, y + 36, x + 11, y + 60, fill="#35444a", width=4, tags="dynamic")
        self.scene.create_polygon(x - 8, y + 11, x + 7, y + 11, x + 12, y + 39, x - 12, y + 39,
                                  fill="#c7463b", outline="#792f2b", width=2, tags="dynamic")
        self.scene.create_line(x - 6, y + 13, x - 12, y + 27, fill="#c7463b", width=4, tags="dynamic")
        self.scene.create_line(x + 7, y + 13, x + 16, y + 23, fill="#c7463b", width=4, tags="dynamic")
        self.scene.create_oval(x - 7, y - 9, x + 7, y + 9, fill="#bd8565", outline="#644c43", width=2, tags="dynamic")
        self.scene.create_polygon(x - 8, y - 5, x + 8, y - 5, x + 5, y - 13, x - 5, y - 13,
                                  fill="#f2bd54", outline="#805b2b", width=2, tags="dynamic")
        self.scene.create_line(x + 15, y + 19, x + 21, y + 9, fill="#8d6940", width=3, tags="dynamic")

    def _draw_automatic_crane(self) -> None:
        trolley_x = self.auto_x
        beam_y = self.auto_y
        self.scene.create_line(trolley_x, auto_scene_y(222), trolley_x, beam_y - 48, fill="#273943", width=3, tags="dynamic")
        self.scene.create_rectangle(trolley_x - 20, auto_scene_y(197), trolley_x + 20, auto_scene_y(222), fill="#d4a956", outline="#5a4b31", width=3, tags="dynamic")
        self.scene.create_line(trolley_x - 15, auto_scene_y(221), trolley_x - 15, auto_scene_y(231), fill="#51452f", width=4, tags="dynamic")
        self.scene.create_line(trolley_x + 13, auto_scene_y(221), trolley_x + 13, auto_scene_y(231), fill="#51452f", width=4, tags="dynamic")
        self.scene.create_rectangle(trolley_x - 9, beam_y - 48, trolley_x + 9, beam_y - 22, fill="#a8b2ae", outline="#394951", width=2, tags="dynamic")
        self.scene.create_rectangle(trolley_x - 12, beam_y - 22, trolley_x + 12, beam_y - 8, fill="#56686e", outline="#394951", width=1, tags="dynamic")
        self.scene.create_rectangle(trolley_x - 41, beam_y - 7, trolley_x + 41, beam_y + 7, fill="#c4a65f", outline="#554a36", width=2, tags="dynamic")
        if self.auto_placements:
            layout = TOWER_LAYOUTS[self.level - 1]
            for index in range(min(3, self.auto_placements)):
                yy = 510 + 1.5 * (layout["targets"][index] - 510)
                self.scene.create_rectangle(815, yy - 7, 901, yy + 7, fill="#c4a65f", outline="#554a36", width=2, tags="dynamic")

    def _draw_bird(self) -> None:
        bird_x = getattr(self, "bird_x", -80)
        bird_y = getattr(self, "bird_y", 205)
        self.scene.create_line(bird_x, bird_y + 5, bird_x + 10, bird_y - 4, bird_x + 20, bird_y + 5,
                               bird_x + 30, bird_y - 4, bird_x + 40, bird_y + 5,
                               fill="#18242a", width=3, smooth=True, tags="dynamic")

    def _draw_graph(self) -> None:
        canvas = self.graph
        canvas.delete("all")
        width, height = 340, 112
        left, right, top, bottom = 40, 329, 8, 83
        canvas.create_rectangle(left, top, right, bottom, outline="#435b67")
        for capacity in (5000, 10000, 15000, 20000):
            y = bottom - (capacity - 5000) / 15000 * (bottom - top)
            canvas.create_line(left, y, right, y, fill="#263d48")
            canvas.create_text(left - 5, y, text=f"{capacity // 1000}k", anchor="e", fill="#9babb5", font=("Segoe UI", 7))
        for radius in (0, 50, 100, 150):
            x = left + radius / 150 * (right - left)
            canvas.create_line(x, top, x, bottom, fill="#1e333e")
            canvas.create_text(x, bottom + 9, text=str(radius), fill="#9babb5", font=("Segoe UI", 7))
        points = []
        for radius, capacity in CAPACITY_CHART:
            x = left + radius / 150 * (right - left)
            y = bottom - (capacity - 5000) / 15000 * (bottom - top)
            points.extend((x, y))
        canvas.create_line(*points, fill="#77d9df", width=2)
        radius = self.trolley_radius()
        capacity = capacity_at_radius(radius)
        x = left + radius / 150 * (right - left)
        cap_y = bottom - (capacity - 5000) / 15000 * (bottom - top)
        canvas.create_line(x, top, x, bottom, fill="#ffd987", dash=(3, 3))
        if self.carried is not None:
            weight = self.beams[self.carried]["weight"]
            load_y = bottom - (max(5000, min(20000, weight)) - 5000) / 15000 * (bottom - top)
            color = "#ff5e59" if weight / capacity >= 0.9 else "#ffd987"
            canvas.create_line(left, load_y, x, load_y, fill=color, dash=(4, 3))
            canvas.create_oval(x - 4, load_y - 4, x + 4, load_y + 4, fill=color, outline="#fff")
            self.graph_note.configure(text=f"{weight:,} lb · {weight / capacity:.0%}", fg=color)
        else:
            canvas.create_oval(x - 4, cap_y - 4, x + 4, cap_y + 4, fill="#ffd987", outline="#fff")
            self.graph_note.configure(text="No beam carried", fg="#9babb5")
        canvas.create_text(183, 102, text="LOAD RADIUS (ft)", fill="#9babb5", font=("Segoe UI", 7, "bold"))

    def _update_hud(self) -> None:
        seconds = max(0, math.ceil(self.remaining))
        blink = int(time.monotonic() * 5) % 2 == 0
        timer_color = "#ffbd62" if seconds > 10 else ("#ff5e59" if blink else "#f5fafb")
        self.stat_values["timer"].configure(text=f"{seconds // 60:02d}:{seconds % 60:02d}", fg=timer_color)
        self.stat_values["score"].configure(text=f"{self.score:,}")
        record_flash = time.monotonic() < self.record_until and blink
        self.stat_values["high"].configure(text=f"{self.high_score:,}", fg="#ffffff" if record_flash else "#ffd987",
                                            bg="#57462d" if record_flash else "#142631")
        self.stat_values["level"].configure(text=f"{self.level} / 5")
        radius = self.trolley_radius()
        capacity = capacity_at_radius(radius)
        percent = self.beams[self.carried]["weight"] / capacity * 100 if self.carried is not None else 0.0
        self.stat_values["radius"].configure(text=f"{radius:.1f} ft")
        warning_flash = percent >= 90 and blink
        self.stat_values["capacity"].configure(text=f"{percent:.0f}% · {capacity:,.0f} lb",
                                               fg="#ff5e59" if warning_flash else "#77d9df")
        self.stat_values["beams"].configure(text=str(3 - len(self.filled_targets)))

    def close(self) -> None:
        if self.running and not self.paused:
            if not messagebox.askyesno("Exit High Steel", "Exit without saving this level?", parent=self.root):
                return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    HighSteelApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
