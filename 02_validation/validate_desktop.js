// Reference checks and milestone graphs for the Tkinter desktop implementation.
// Run from the project root with: node 02_validation/validate_desktop.js
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "..");
const step = Number(process.argv[2] || 1);
assert.ok(Number.isInteger(step) && step >= 1 && step <= 3, "Step must be 1, 2, or 3");
const appSource = fs.readFileSync(path.join(root, "04_desktop", "app.py"), "utf8");
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

let feasibleRoutes = 0;
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
  assert.match(appSource, /def save_progress\(/);
  assert.match(appSource, /def load_progress\(/);
  assert.match(appSource, /def make_checkpoint\(/);
  assert.match(appSource, /def validate_checkpoint\(/);
  assert.match(appSource, /"placed_targets": sorted\(placed_targets\)/);
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
fs.writeFileSync(path.join(outDir, `capacity-validation-step-${step}.svg`), graphSvg(`Step ${step}`), "utf8");
console.log(JSON.stringify({ step, checks, feasibleRoutes, appSourceChecks: "passed", graphWritten: 1 }, null, 2));
