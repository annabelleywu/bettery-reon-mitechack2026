# User guide: the REON Cell Bypass Explorer

A dashboard that shows what REON's cell-level control is worth to a Massachusetts commercial battery owner, compared with the same cells in a conventional battery.

## 1. Open the dashboard

GitHub shows the dashboard's code, not the page itself. Use one of these:

| Option | How |
|---|---|
| **Published link (easiest)** | https://claude.ai/artifact/2uKjEAMjq2JzoyPa3ejHJd |
| **GitHub Pages** (once the repo owner turns it on) | https://annabelleywu.github.io/mitec2026/webapp/ |
| **Download** | On GitHub: green **Code** button → **Download ZIP** → unzip → double-click `webapp/index.html`. It opens in any browser; no install or internet needed. |

Turning on GitHub Pages (repo owner, one minute): **Settings → Pages → Build and deployment → Source: Deploy from a branch → choose the default branch and `/ (root)` → Save.** The page appears at the address above a minute later.

The dashboard simulates batteries in your browser. Give it a few seconds after opening or after moving a slider ("Simulating…" in the top right).

## 2. The story in three steps

The **Customer view** opens with these three panels:

1. **The problem.** A conventional battery wires all its cells in one line. The weakest cell decides how much energy the battery can give and when the battery must be replaced, and one failed cell stops all 250.
2. **What REON changes.** REON senses and switches every cell. An empty cell steps aside while the others keep discharging, and 25 backup cells (10% of the string, as REON described its design) take over from any that fail.
3. **What it is worth.** More usable energy, a longer-lasting battery and no single-cell outages, turned into dollars and CO₂ for a real Massachusetts customer.

## 3. Customer view (for owners, judges and REON's sales team)

**Pick a customer** with the buttons:

| Button | Site | Utility rate |
|---|---|---|
| Neighborhood grocer | Refrigeration-heavy small business, 2 REON EBS blocks (60 kW / 120 kWh) | Eversource G-1 demand option, $41.65 per kW of monthly peak |
| Mid-size business (default) | 2 blocks | Eversource G-2, $33.95/kW |
| Cold-storage warehouse | Large site such as a regional cold store, 10 blocks | Eversource G-3, $30.05/kW |

**Include cell failures (REON's 2–3× case)** switches on random cell failures (0.1% per cell per year). A conventional battery is then replaced at its first failure, because one failed cell stops it. Turn it on to see where REON's 2–3× claim comes from; turn it off for aging alone.

**The cards.** Hover over **ⓘ** on any card to see how it is calculated; the links under each card go to its sources.

| Card | What it means |
|---|---|
| Extra value over 20 years | REON's net present value minus the conventional battery's, after REON's higher BMS cost. Both owners buy a new battery when the old one retires. The range (P10 to P90) is the spread over simulated batteries. |
| System cycle life | Years (and cycles) until the battery can deliver less than 70% of its rated energy. |
| Energy delivered per battery | Total energy each battery delivers before it retires. |
| Batteries worn out over 20 years | How many battery-lifetimes the site uses up; fewer means fewer replacements and fewer cells manufactured. |
| Usable capacity at year 5 | How much of the battery the customer can actually use (its real depth of discharge). |
| Round-trip efficiency | Energy out per energy in; REON's per-cell switches cost a little. |
| Payback | Years until savings repay the purchase, after the 30% federal tax credit. |
| Chance one cell stops the battery | Over 10 years, for a conventional battery, against about zero with REON's backup cells. |
| CO₂ avoided, cells kept out of waste | From extra clean energy delivered and batteries not manufactured. |
| 20-year value, conventional / REON | The two totals behind the first card. |

**Assumptions and sources** at the bottom lists every input, its value, whether it is data, from REON, sourced or assumed, and a link to the source.

## 4. Engineering view (for REON's engineers and anyone checking the model)

A short "How to read this view" note sits at the top. Then:

- **Left: every assumption as a slider**, grouped by topic (pack and string, retirement, Massachusetts site economics, REON's BMS cost, control policy, per-cell monitoring, cell aging, hard cell failures, simulation). Grey notes give each input's source or status. **Reset to defaults** undoes everything; a second button loads REON's 2–3× case.
- **Four tiles**: service life, lifetime energy, firm power and power utilization, conventional (grey, left) against REON (blue, right).
- **Value table**: year-1 revenue by program, payback, NPV over each battery's own life, and the 20-year comparison with replacements.
- **Rings**: each spoke is one cell. Press **Play** to watch cells age; grey is energy the conventional string strands because its weakest cell is empty.
- **Usable energy over the battery's life**: median and range for both designs, with the 70% retirement line.
- **Three sweeps**: how the gain depends on the number of backup cells, on cell-to-cell spread (how uneven the cells are) and on resting cells. The red dashed line is break-even against REON's extra BMS cost.
- **Assumptions and sources**: the same table as the Customer view.

## 5. A two-minute tour

1. Customer view, default site: about +12% energy and +11% life per battery, about +$4k per site over 20 years.
2. Click **Cold-storage warehouse**: ten blocks, about five times the value.
3. Click **Include cell failures**: the conventional battery's life roughly halves and REON's value jumps (REON's 2–3× claim).
4. Hover over **ⓘ** on "Chance one cell stops the battery".
5. Engineering view → move **Backup cells k** from 25 to 5, then to 125, and watch the gain shrink and grow.
6. Move **Cell-to-cell spread, multiple of the calibrated spread** (under Cell aging) to 2×: more uneven cells make REON worth more.

## 6. Which numbers to quote

The dashboard simulates 48 batteries per design so the sliders stay fast, so its numbers move by about ±0.5 points between settings. **The official numbers come from the Python model at 2,000 batteries per design** in [`outputs/value_summary.md`](../outputs/value_summary.md). The two agree within about 0.3 points and $300 at equal settings (`node webapp/checks/crosscheck.js`). The method, every source and the limitations are in [`docs/Methodology_v2.md`](Methodology_v2.md).

Estimates under stated assumptions, not REON performance claims.
