# User guide: the C&I Battery Cell Bypass Explorer

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
| NE Cold Storage (illustrative) | Independent frozen and refrigerated warehouse in Sturbridge, MA; 2 blocks; no solar on site. Tagged "Illustrative: inputs to be confirmed with NE Cold"; peak kW, monthly kWh, rate class and block count are placeholders | National Grid G-2, $15.06/kW (the closest model case) |
| Neighborhood grocer | Refrigeration-heavy small business, 2 REON EBS blocks (60 kW / 120 kWh) | Eversource G-1 demand option, $41.65 per kW of monthly peak |
| Mid-size business (default) | 2 blocks | Eversource G-2, $33.95/kW |
| Cold-storage warehouse | Large site such as a regional cold store, 10 blocks | Eversource G-3, $30.05/kW |

**Which scenario?** Two cards decide what the numbers assume:
- **Normal aging** (default): cells wear out at slightly different speeds, as measured in real electric-vehicle batteries; no cell fails suddenly. This is the base case.
- **Aging plus cell failures:** also assumes about 1 in 1,000 cells fails each year (an assumption; no public field data) and a conventional battery is replaced whenever one cell fails. Our model then gives REON roughly 2× the energy and life, in the range of the 2–3× REON states; we do not know how REON measured theirs, so treat it as an upside scenario, not a replication. The recommendation panel carries a tag naming the scenario.

**The recommendation panel** (dark green) answers the customer's question in one line: which option comes out ahead over 20 years, and by how much (with the range across simulated batteries). Beside it, **What decides it** lists:
- **The trade.** What REON's cell-level control adds to the upfront price after the tax credit (about $2,000 for the default site) against how far ahead the customer is after 20 years once that extra cost and replacements are counted. The "The trade" card below shows it as two numbers and two bars.
- **The physical gains.** Battery life, energy delivered and single-cell failure protection.
- **The main risk.** Per-cell switch losses: at 1 mΩ per switch the gain turns negative, so this is the number to confirm with REON.

**Six at-a-glance tiles.** Paired bars for net value, battery life, energy delivered, payback, batteries bought and the chance one cell stops the battery; green text marks where REON is better, red where it is not.

**Two cards.** A line chart of usable energy over time (each line ends when that battery is replaced) and "The trade": the extra upfront cost against the net gain. An **Inside one REON block** line near the top shows 250 cells, 25 spare cells and 60 kWh / 30 kW (our picks inside REON's stated 200–300 cells per string and about 10% spares; to be confirmed with REON). The price REON could charge and still pay off ("price headroom") is in the Engineering view, since it is a pricing question for REON, not for the customer.

**Side-by-side table.** One column for a conventional battery and one for REON with the same cells, site and tariff, plus a difference column. A ✓ marks the better option on each line. Hover over (or tap) **ⓘ** to see how a line is calculated; the links under each line go to its sources.

| Group | Lines |
|---|---|
| Money over 20 years | Net value to the owner (present value of earnings minus purchases, replacements and O&M), upfront price after the 30% tax credit, payback, batteries bought over 20 years |
| Battery performance | Service life (years and cycles to 70% of rated energy), energy delivered over one battery's life, usable capacity at year 5, round-trip efficiency |
| Reliability | Chance one failed cell stops the battery in 10 years |
| Environment | Energy delivered over 20 years, battery capacity used up (with its manufacturing CO₂ and cell mass), total CO₂ avoided with REON |

**Solar is optional.** The dollar results do not depend on on-site solar (they come from demand charges, ConnectedSolutions, Clean Peak and battery losses). Solar affects only the operating-CO₂ credit, through the Engineering view setting **Share of battery charging from on-site solar**: 100% for a solar-paired site (the default), 0% for a grid-only site such as NE Cold, where only the CO₂ of cells not manufactured counts.

REON is not better on every line: it costs a little more upfront and its switches lose a little energy. The table shows those trade-offs next to the gains so a customer can weigh them.

**Assumptions and sources** (a fold-out at the bottom of the Customer view, always open in the Engineering view) lists every input, its value, whether it is data, from REON, sourced or assumed, and a link to the source.

## 4. Engineering view (for REON's engineers and anyone checking the model)

A short "How to read this view" note sits at the top. Then:

- **Left: every assumption as a slider**, grouped by topic (pack and string, retirement, Massachusetts site economics, REON's BMS cost, control policy, per-cell monitoring, cell aging, hard cell failures, simulation). Grey notes give each input's source or status. **Reset to defaults** undoes everything; a second button loads REON's 2–3× case.
- **Four tiles**: service life, lifetime energy, firm power and power utilization, conventional (grey, left) against REON (green, right).
- **Value table**: year-1 revenue by program, payback, NPV over each battery's own life, and the 20-year comparison with replacements.
- **Rings**: each spoke is one cell. Press **Play** to watch cells age; grey is energy the conventional string strands because its weakest cell is empty.
- **Usable energy over the battery's life**: median and range for both designs, with the 70% retirement line.
- **Three sweeps**: how the gain depends on the number of backup cells, on cell-to-cell spread (how uneven the cells are) and on resting cells. The red dashed line is break-even against REON's extra BMS cost.
- **Assumptions and sources**: the same table as the Customer view.

## 5. A two-minute tour

1. Customer view, default site: about +12% energy and +11% life per battery, about +$4k per site over 20 years.
2. Click **NE Cold Storage (illustrative)** for the sales-meeting story: a National Grid site with no solar, about +$3.4k over 20 years in the dashboard (+$3.5k in the Python model). Then click **Cold-storage warehouse**: ten blocks, about five times the value of two.
3. Choose **Aging plus cell failures**: the conventional battery's life roughly halves and REON's value jumps (in the range of REON's stated 2–3×; we do not claim to replicate their figure).
4. Read the recommendation panel and the "The trade" card: a small extra upfront cost against the net gain after 20 years.
5. Engineering view → move **Backup cells k** from 25 to 5, then to 125, and watch the gain shrink and grow.
6. Move **Cell-to-cell spread, multiple of the calibrated spread** (under Cell aging) to 2×: more uneven cells make REON worth more.

## 6. Which numbers to quote

The dashboard simulates 48 batteries per design so the sliders stay fast, so its numbers move by about ±0.5 points between settings. **The official numbers come from the Python model at 2,000 batteries per design** in [`outputs/value_summary.md`](../outputs/value_summary.md). The two agree within about 0.3 points and $300 at equal settings (`node webapp/checks/crosscheck.js`). The method, every source and the limitations are in [`docs/Methodology_v2.md`](Methodology_v2.md).

Estimates under stated assumptions, not REON performance claims.

## 7. Customer view vs Engineering view wording

The Customer view is written for a site owner: no percentile ranges or modelling caveats on the page. Those live in the ⓘ tooltips, the "Assumptions and sources" fold-out, the Engineering view and these docs. The Engineering view also shows REON's price headroom and, above each cell ring, when that battery becomes unusable (below 70% of rated energy, or a failed cell in the failure scenario).
