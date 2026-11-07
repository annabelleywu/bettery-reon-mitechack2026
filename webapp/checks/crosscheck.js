// Python vs browser agreement on the team default (paired packs, faults off).
// Compares against the headline in outputs/value_summary.md (Python). Exits 1 if they disagree
// by more than the tolerance. Usage: node webapp/checks/crosscheck.js [packs=2000]
const fs = require("fs"), path = require("path");
const M = require("./load_model");
const packs = +(process.argv[2] || 2000), p = M.clone(M.DEFAULTS);
const F = [], C = [];
for (let i = 0; i < packs; i++) { F.push(M.simPack(p, "fixed", i, false)); C.push(M.simPack(p, "cell", i, false)); }
const mean = a => a.reduce((s, x) => s + x, 0) / a.length;
const js = {
  energy: 100 * (mean(C.map(x => x.mwh)) / mean(F.map(x => x.mwh)) - 1),
  life: 100 * (mean(C.map(x => x.life)) / mean(F.map(x => x.life)) - 1),
  npv: M.pct(C.map((x, i) => M.econPack(x, "cell", p).npv - M.econPack(F[i], "fixed", p).npv), 0.5) * p.nBlocks / 1000,
};
const md = fs.readFileSync(path.join(__dirname, "..", "..", "outputs", "value_summary.md"), "utf8");
const num = re => { const m = md.match(re); return m ? parseFloat(m[1].replace(/,/g, "")) : NaN; };
const py = {
  energy: num(/Lifetime energy gain \*\*([+-]?[\d.]+)%/),
  life: num(/service life gain \*\*([+-]?[\d.]+)%/),
  npv: num(/NPV gain from cell-level control: \*\*\$([\d,.-]+)\*\*/) / 1000,
};
const tol = { energy: 0.5, life: 0.5, npv: 0.5 };   // points, points, $k: about 2 standard errors at these pack counts
let ok = true;
console.log(`metric        browser (${packs})   python   tolerance`);
for (const k of ["energy", "life", "npv"]) {
  const d = Math.abs(js[k] - py[k]); if (!(d <= tol[k])) ok = false;
  console.log(`${k.padEnd(12)}  ${js[k].toFixed(2).padStart(8)}   ${py[k].toFixed(2).padStart(8)}   ±${tol[k]}  ${d <= tol[k] ? "ok" : "DISAGREE"}`);
}
console.log("(energy and life in %, NPV gain in $k per site)");
process.exit(ok ? 0 : 1);
