// Reference checks and milestone graphs for the Tkinter desktop implementation.
// Run from the project root with: node 02_validation/validate_desktop.js
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const step = Number(process.argv[2] || 1);
assert.ok(Number.isInteger(step) && step >= 1 && step <= 3, "Step must be 1, 2, or 3");
const appSource = fs.readFileSync(path.join(root, "04_desktop", "app.py"), "utf8");
const renderSource = fs.readFileSync(path.join(root, "04_desktop", "render_scenes.ps1"), "utf8");
const chart = [[0, 20000], [50, 20000], [75, 13000], [100, 9000], [125, 7000], [150, 5500]];
const layouts = [
  { centers: [720, 720, 720] }, { centers: [713, 727, 717] },
  { centers: [727, 712, 724] }, { centers: [711, 729, 713] }, { centers: [727, 713, 723] }
];
const ranges = [[155, 205], [360, 470], [520, 660]];

function capacity(radius) {
  const r = Math.min(150, Math.max(0, radius));
  for (let i = 1; i < chart.length; i += 1) {
    const [r0, c0] = chart[i - 1];
    const [r1, c1] = chart[i];
    if (r <= r1) return c0 + ((r - r0) / (r1 - r0)) * (c1 - c0);
  }
  return chart.at(-1)[1];
}
const radiusAtX = (x) => Math.min(150, Math.abs(x - 310) * 150 / 500);
const checks = [];
function check(name, expected, actual, tolerance = 0.01) {
  const passed = Math.abs(expected - actual) <= tolerance;
  checks.push({ name, expected, actual, passed });
  assert.ok(passed, `${name}: expected ${expected}, got ${actual}`);
}

check("Capacity at 50 ft", 20000, capacity(50));
check("Capacity at 62.5 ft", 16500, capacity(62.5));
check("Capacity at 74.99 ft", 13002.8, capacity(74.99));
check("Capacity at 75.01 ft", 12998.4, capacity(75.01));
check("Capacity at 112 ft", 8040, capacity(112));
check("90% warning at 112 ft", 7236, capacity(112) * 0.9);
check("Capacity at 123 ft", 7160, capacity(123));
check("Capacity at 150 ft", 5500, capacity(150));

// These properties are checked for every step, including the final review.
const propertyChecks = [];
let proportionalitySamples = 0;
for (let i = 1; i < chart.length; i += 1) {
  const [r0, c0] = chart[i - 1];
  const [r1, c1] = chart[i];
  for (const fraction of [0.25, 0.5, 0.75]) {
    const expected = c0 + fraction * (c1 - c0);
    const actual = capacity(r0 + fraction * (r1 - r0));
    assert.ok(Math.abs(expected - actual) < 1e-8,
      `Interpolation proportionality failed in ${r0}-${r1} ft segment at ${fraction}`);
    proportionalitySamples += 1;
  }
}
propertyChecks.push({ name: "Linear interpolation proportionality", samples: proportionalitySamples, passed: true });

let symmetrySamples = 0;
for (const offset of [25, 75, 150, 300]) {
  const leftRadius = radiusAtX(310 - offset);
  const rightRadius = radiusAtX(310 + offset);
  assert.ok(Math.abs(leftRadius - rightRadius) < 1e-8,
    `Trolley-radius symmetry failed at ${offset} scene units`);
  assert.ok(Math.abs(capacity(leftRadius) - capacity(rightRadius)) < 1e-8,
    `Capacity symmetry failed at ${offset} scene units`);
  symmetrySamples += 1;
}
propertyChecks.push({ name: "Left/right trolley-radius and capacity symmetry", samples: symmetrySamples, passed: true });

let feasibleRoutes = 0;
const stepTwoSourceChecks = [];
function sourceCheck(name, pattern) {
  assert.match(appSource, pattern, name);
  stepTwoSourceChecks.push(name);
}
if (step >= 2) {
  for (let level = 1; level <= 5; level += 1) {
    for (let beam = 0; beam < 3; beam += 1) {
      const [xmin, xmax] = ranges[beam];
      const weight = beam === 0 ? 3250 + 500 * (level - 1) + 250
        : beam === 1 ? 4250 + 500 * (level - 1) + 250
          : 5750 + 250 * (level - 1);
      for (let x = xmin; x <= xmax; x += 5) {
        const routeRadius = Math.max(radiusAtX(x), radiusAtX(layouts[level - 1].centers[beam]));
        assert.ok(weight < capacity(routeRadius), `Unsafe route: level ${level}, beam ${beam + 1}, pickup ${x}`);
        feasibleRoutes += 1;
      }
    }
  }
  assert.equal(feasibleRoutes, 315, "All 315 pickup-to-target routes must be checked");
  check("Challenge beam above 150 ft capacity", 250, 5750 - capacity(150));
  check("Challenge beam below 123 ft capacity", 1410, capacity(123) - 5750);

  const mirrorX = (x, scale) => 310 + (x - 310) * scale;
  for (const x of [190, 221, 286, 334, 465, 817]) {
    assert.equal(mirrorX(mirrorX(x, -1), -1), x, `Crane mirror must be reversible at x=${x}`);
  }
  assert.equal(mirrorX(465, -1), 155, "Mirrored trolley must reach the left beam's near spawn");
  assert.equal(mirrorX(415, -1), 205, "Mirrored trolley must reach the left beam's far spawn");
  propertyChecks.push({ name: "Crane mirror reversibility and left-beam reach", samples: 8, passed: true });

  const turnScale = (progress) => Math.cos(Math.PI * progress);
  for (const fraction of [0, 0.25, 0.5, 0.75, 1]) {
    assert.ok(Math.abs(turnScale(fraction) + turnScale(1 - fraction)) < 1e-10,
      `Turn must be symmetric around its edge-on midpoint at ${fraction}`);
  }
  assert.ok(Math.abs(turnScale(0.5)) < 1e-10, "Halfway turn must be edge-on");
  propertyChecks.push({ name: "Turn animation symmetry around edge-on midpoint", samples: 5, passed: true });
}
assert.match(appSource, /CAPACITY_CHART\s*=\s*\(\(0, 20000\), \(50, 20000\), \(75, 13000\), \(100, 9000\), \(125, 7000\), \(150, 5500\)\)/);
assert.match(appSource, /def capacity_at_radius\(/);
assert.match(appSource, /def player_scene_y\(/);
assert.match(appSource, /def auto_scene_y\(/);
assert.match(appSource, /def _draw_graph\(/);
assert.match(appSource, /def trolley_radius\(self\).*return scene_radius\(self\._screen_trolley_x\(\)\)/s);
assert.equal((appSource.match(/radius = self\.trolley_radius\(\)/g) || []).length, 3);
assert.doesNotMatch(appSource, /scene_radius\(self\._load_x\(\)\)/);
assert.match(appSource, /self\.root\.grid_rowconfigure\(1, weight=1\)/);
assert.match(appSource, /footer\.grid\(row=2, column=0, sticky="ew"/);
assert.match(appSource, /self\.scene_scale = next\(/);
assert.match(appSource, /self\._scale_scene_items\("dynamic"\)/);
assert.doesNotMatch(appSource, /tk\.Scrollbar\(/);
assert.match(appSource, /self\.scene\.itemconfigure\(self\.background_item, image=self\.background_images\[self\.level - 1\]\)/);
if (step >= 2) {
  sourceCheck("Five level timers", /LEVEL_SECONDS\s*=\s*\(120, 90, 60, 45, 30\)/);
  sourceCheck("Beam placement and level bonus", /self\.score \+= 100[\s\S]*?self\.score \+= 200/);
  sourceCheck("Worker and automatic crane penalties", /if worker_hit and not self\.last_worker_contact:[\s\S]*?if auto_hit and not self\.last_auto_contact:/);
  sourceCheck("Bird strike triggers sway at trolley cable", /abs\(self\.bird_x \+ 20 - self\._screen_trolley_x\(\)\) < 22[\s\S]*?self\.sway_started = now/);
  sourceCheck("Pause gates checkpoint save", /def save_progress\(self\)[\s\S]*?if not self\.paused:/);
  sourceCheck("Portable JSON checkpoint", /def make_checkpoint\([\s\S]*?"placed_targets": sorted\(placed_targets\)[\s\S]*?"placements":/);
  sourceCheck("Checkpoint rejects completed or expired level", /not 0 < remaining <= LEVEL_SECONDS\[level - 1\][\s\S]*?len\(targets\) >= 3/);
  sourceCheck("Checkpoint load regenerates remaining beams", /def load_progress\(self\)[\s\S]*?validate_checkpoint\(data\)[\s\S]*?self\._begin_level\([^\n]*targets, placed_beams\)/);
  sourceCheck("Blocked target keeps carried beam", /if target_index is not None and self\._auto_blocks_target\(target_index\):[\s\S]*?return/);
  sourceCheck("Timer uses full elapsed time", /self\.remaining = max\(0\.0, self\.remaining - frame_delta\)/);
  sourceCheck("Scheduled timer loop can be cancelled", /def _cancel_tick\(self\)[\s\S]*?self\.root\.after_cancel\(self\.tick_after_id\)/);
  sourceCheck("Pending level transition can be cancelled", /if self\.level_after_id is not None:[\s\S]*?self\.root\.after_cancel\(self\.level_after_id\)/);
  sourceCheck("Time left card sits beside the header title", /text="Build above the skyline"[\s\S]*?timer_card = tk\.Frame\(header,[\s\S]*?timer_card\.pack\(side="left"[\s\S]*?self\.stat_values\["timer"\] = timer_value/);
  sourceCheck("Player crane body is drawn every frame", /def _draw_scene\(self\) -> None:\s+self\.scene\.delete\("dynamic"\)\s+self\._draw_player_crane\(\)/);
  sourceCheck("Crane mirror uses mast pivot and eased turn", /def crane_scene_x\([\s\S]*?return MAST_PIVOT \+ \(local_x - MAST_PIVOT\) \* visual_scale[\s\S]*?def crane_turn_scale\([\s\S]*?math\.cos\(math\.pi \* fraction\)/);
  sourceCheck("Trolley follows animated crane mirror", /def _screen_trolley_x\(self\)[\s\S]*?return crane_scene_x\(self\.trolley_x, self\._visual_crane_scale\(\)\)/);
  assert.match(renderSource, /<style>#player-crane,/, "Static scene must omit the fixed player crane");
  stepTwoSourceChecks.push("Static scene omits fixed player crane");
  assert.doesNotMatch(appSource, /\("timer", "TIME LEFT"\)/);
}
for (let level = 1; level <= 5; level += 1) {
  for (const percent of [60, 70, 80, 90, 100]) {
    const png = fs.readFileSync(path.join(root, "04_desktop", "assets", `scene-level-${level}-${percent}.png`));
    assert.equal(png.readUInt32BE(16), 1440 * percent / 100, `level ${level}, ${percent}% scene width`);
    assert.equal(png.readUInt32BE(20), 660 * percent / 100, `level ${level}, ${percent}% scene height`);
  }
}

const outDir = path.join(root, "03_output");
fs.mkdirSync(outDir, { recursive: true });
function graphSvg(stepLabel) {
  const w = 900, h = 480, left = 78, right = 860, top = 42, bottom = 394;
  const x = (radius) => left + radius / 150 * (right - left);
  const y = (lbs) => bottom - (lbs - 5000) / 15000 * (bottom - top);
  const curve = chart.map(([r, c]) => `${x(r)},${y(c)}`).join(" ");
  const marks = [
    [50, "50 ft", -38, 18], [62.5, "62.5 ft", 8, -14], [74.99, "74.99 ft", -116, 15],
    [75.01, "75.01 ft", 8, -22], [112, "112 ft", -80, 16], [123, "123 ft", 8, -14], [150, "150 ft", -97, 20]
  ].map(([r, label, dx, dy]) => {
    const cy = y(capacity(r));
    const tx = Math.min(right - 112, Math.max(left + 3, x(r) + dx));
    const ty = Math.min(bottom - 4, Math.max(top + 12, cy + dy));
    return `<circle cx="${x(r)}" cy="${cy}" r="4" fill="#ffbd62" stroke="#08131d" stroke-width="2"/><text x="${tx}" y="${ty}" fill="#e7eff2" font-size="11">${label}: ${Math.round(capacity(r)).toLocaleString()} lb</text>`;
  }).join("");
  const grid = [5000, 7500, 10000, 12500, 15000, 17500, 20000].map((v) =>
    `<line x1="${left}" y1="${y(v)}" x2="${right}" y2="${y(v)}" stroke="#29414d"/><text x="${left - 10}" y="${y(v) + 4}" text-anchor="end" fill="#9babb5" font-size="11">${v.toLocaleString()}</text>`).join("");
  const xTicks = [0, 25, 50, 75, 100, 125, 150].map((v) =>
    `<line x1="${x(v)}" y1="${top}" x2="${x(v)}" y2="${bottom}" stroke="#213843"/><text x="${x(v)}" y="${bottom + 20}" text-anchor="middle" fill="#9babb5" font-size="11">${v}</text>`).join("");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="900" height="480" viewBox="0 0 900 480" style="font-family:Segoe UI,Arial,sans-serif"><rect width="900" height="480" rx="12" fill="#101e29"/><text x="40" y="26" fill="#dce8eb" font-size="15" font-weight="700">${stepLabel} · Capacity validation</text>${grid}${xTicks}<polyline points="${curve}" fill="none" stroke="#77d9df" stroke-width="4" stroke-linejoin="round"/>${marks}<text x="469" y="455" text-anchor="middle" fill="#dce8eb" font-size="13">Load radius (ft)</text><text transform="translate(21 218) rotate(-90)" text-anchor="middle" fill="#dce8eb" font-size="13">Maximum capacity (lb)</text><line x1="650" y1="30" x2="685" y2="30" stroke="#77d9df" stroke-width="4"/><text x="692" y="34" fill="#dce8eb" font-size="11">Capacity curve</text><circle cx="827" cy="30" r="4" fill="#ffbd62"/><text x="838" y="34" fill="#dce8eb" font-size="11">Validation</text></svg>`;
}
function addPropertySamples(svg) {
  const x = (radius) => 78 + radius / 150 * (860 - 78);
  const y = (lbs) => 394 - (lbs - 5000) / 15000 * (394 - 42);
  const dots = chart.slice(1).map(([r1, c1], index) => {
    const [r0, c0] = chart[index];
    return [0.25, 0.5, 0.75].map((fraction) => {
      const radius = r0 + fraction * (r1 - r0);
      const expected = c0 + fraction * (c1 - c0);
      return `<circle cx="${x(radius)}" cy="${y(expected)}" r="3" fill="#79d7ac" stroke="#101e29" stroke-width="1"/>`;
    }).join("");
  }).join("");
  return svg.replace(/<polyline[^>]*\/>/, (line) => line + dots)
    .replace('<text x="469" y="455"',
      '<text x="680" y="432" text-anchor="end" fill="#79d7ac" font-size="11">Green dots: 15 proportionality checks</text><text x="469" y="455"');
}
fs.writeFileSync(path.join(outDir, `capacity-validation-step-${step}.svg`), addPropertySamples(graphSvg(`Step ${step}`)), "utf8");
console.log(JSON.stringify({ step, checks, propertyChecks, feasibleRoutes, appSourceChecks: "passed", stepTwoSourceChecks, graphWritten: 1 }, null, 2));
