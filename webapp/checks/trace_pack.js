// One pack, month by month: re-derives the cell-level design's usable energy by hand from the trace
// (sum over active cells of min(Q_i, stop), stop = (h+1)-th weakest active cell) and checks the
// resting rule targets the cells that end up weakest. Usage: node webapp/checks/trace_pack.js [pack=3]
const M = require("./load_model");
const p = M.clone(M.DEFAULTS), N = p.N, pk = +(process.argv[2] || 3);
const f = M.simPack(p, "fixed", pk, true), c = M.simPack(p, "cell", pk, true);
const cellAh = p.blockKWh * 1000 / (N * 3.1);
let bad = 0;
console.log("month  fixed kWh  cell kWh  resting  bypassed  stop Q   by hand");
for (let k = 0; k < M.K; k++) {
  const st = Array.from(c.tr.st.subarray(k * N, (k + 1) * N)), Q = Array.from(c.tr.Q.subarray(k * N, (k + 1) * N));
  const rest = st.filter(s => s === 1).length, byp = st.filter(s => s >= 2).length;
  const act = Q.filter((q, i) => st[i] === 0).sort((a, b) => a - b);
  const stop = act[Math.min(Math.max(0, p.k - byp - rest), act.length - 1)];
  const hand = Q.reduce((s, q, i) => s + (st[i] === 0 ? Math.min(q, stop) : 0), 0) * cellAh * 3.1 / 1000 * p.eff / 100;
  if (Math.abs(hand - c.energy[k]) > 1e-3) bad++;   // trace stores Q as float32
  const lf = Math.round(f.life * 12), lc = Math.round(c.life * 12);
  if (k % 12 === 0 || k === lf || k === lc)
    console.log(`${String(k).padStart(5)}  ${f.energy[k].toFixed(2).padStart(9)}  ${c.energy[k].toFixed(2).padStart(8)}  ${String(rest).padStart(7)}  ${String(byp).padStart(8)}  ${stop.toFixed(4)}  ${hand.toFixed(2).padStart(7)}` +
      (k === lf ? "  <- fixed string retires" : "") + (k === lc ? "  <- cell-level retires" : ""));
  if (k > lc) break;
}
console.log(`hand-check mismatches: ${bad}`);
let hits = 0, tot = 0;
for (let q = 0; q < 200; q++) {
  const cc = M.simPack(p, "cell", q, true), ff = M.simPack(p, "fixed", q, true), kk = Math.min(Math.round(ff.life * 12), M.K - 1);
  const weak = new Set(Array.from(ff.tr.Q.subarray(kk * N, (kk + 1) * N)).map((v, i) => [v, i]).sort((a, b) => a[0] - b[0]).slice(0, 10).map(x => x[1]));
  const rested = new Set(); for (let k = 0; k < M.K; k++) for (let i = 0; i < N; i++) if (cc.tr.st[k * N + i] === 1) rested.add(i);
  for (const i of rested) { tot++; if (weak.has(i)) hits++; }
}
console.log(`resting targets: ${(100 * hits / tot).toFixed(0)}% of rested cells are among the 10 weakest at the fixed twin's retirement (random: 10%)`);
