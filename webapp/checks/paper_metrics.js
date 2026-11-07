// Fixed string in stationary use vs Zhou et al. (Nature Energy 2026) fleet metrics.
// beta_life: time the first cell reaches 0.85 / mean cell time to 0.85 (paper's EOL; censored at 20 y).
// beta_energy = beta_life x <beta_SOC>; the model has no SOC imbalance (beta_SOC = 1; paper: > 0.98).
// beta_power at beginning of life (paper eq. 12-16, simplified). Usage: node webapp/checks/paper_metrics.js [packs=400]
const M = require("./load_model");
const p = M.clone(M.DEFAULTS), N = p.N, n = +(process.argv[2] || 400);
const bl = [], bp = [];
for (let pk = 0; pk < n; pk++) {
  const x = M.simPack(p, "fixed", pk, true), Q = x.tr.Q, t = new Float64Array(N).fill(M.YEARS);
  for (let i = 0; i < N; i++) for (let k = 0; k < M.K; k++) if (Q[k * N + i] < 0.85) { t[i] = k * M.DT; break; }
  bl.push(Math.min(...t) / (t.reduce((a, b) => a + b, 0) / N)); bp.push(x.bpow[0]);
}
const avg = a => a.reduce((s, x) => s + x, 0) / a.length, sd = a => Math.sqrt(avg(a.map(x => (x - avg(a)) ** 2)));
console.log(`beta_life    model ${avg(bl).toFixed(3)} (sd ${sd(bl).toFixed(3)})   paper cars 0.823 (sd 0.033)`);
console.log(`beta_energy  model ${avg(bl).toFixed(3)} (beta_SOC = 1)    paper cars 0.807 (incl. beta_SOC ~0.98)`);
console.log(`beta_power   model ${avg(bp).toFixed(3)} at beginning of life   paper fleet 0.871 (cars), 0.849 (buses)`);
