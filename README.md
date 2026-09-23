# Cafe Menu Planning Tool

This is a planning tool for small cafe owners that uses linear programming and Monte Carlo simulation to recommend how many of each drink to prepare daily. You give it your menu, ingredient costs, and daily constraints (budget and labor hours), and it tells you what to make and how confident it is in that recommendation.

Built as a data science portfolio project.

---

## What it does

**Deterministic solve** finds the theoretical best-case production plan that maximises profit within your daily budget and labor constraints.

**Monte Carlo simulation** runs the optimiser 2,000 times across randomly sampled demand scenarios to give you a realistic profit forecast with uncertainty ranges instead of a single overconfident number.

**Manual overrides** let you pin any drink to a specific quantity (e.g. for a group booking) and the solver will re-optimise the rest of the budget around it.

---

## Example output

```
──────────────── Cafe Daily Planning Report ────────────────

                          Recommendations
  Drink                         Rec Qty  90% Range  Unit Profit  Confidence
 ─────────────────────────────────────────────────────────────────────────
  Iced Strawberry Matcha Latte       5    5 - 14       $8.40       ⚠ LOW
  Iced Coconut Matcha Foam           6    5 - 17       $9.00       ⚠ LOW
  Iced Salted Caramel Shaken Esp    28   15 - 39       $7.85       ⚠ LOW
  Iced White Mocha                   5   11 - 30       $7.30       ⚠ LOW
  Iced Oat Milk London Fog          48   10 - 30       $7.60       ⚠ LOW

  Profit Forecast
    Median:       $659.12
    90% interval: $606.63 - $689.05
    Deterministic ceiling: $717.10

  Constraints
    Budget:  $149.90 / $150.00  (99.9%)  <- bottleneck
    Labor:   341 min / 480 min  (71.0%)

  Monte Carlo: 1994/2000 runs solved
```

> The LOW confidence flags are expected at this stage. They reflect how wide the demand estimates are since we're working off benchmarks rather than real sales history. Once you have actual data, those ranges will tighten up.

---

## Tech stack

| Layer | Tool |
|---|---|
| Optimisation solver | PuLP (CBC) |
| Demand simulation | NumPy + SciPy (triangular distribution) |
| Config | PyYAML |
| CLI output | Rich |
| Testing | pytest |

---

## Project structure

```
LP-app/
├── cli.py                  # entry point
├── data/
│   └── menu.yaml           # products, costs, prices, demand distributions, constraints
├── solver/
│   ├── model.py            # LP model (PuLP)
│   └── monte_carlo.py      # Monte Carlo simulation wrapper
└── tests/
    ├── test_solver.py      # LP correctness tests
    └── test_monte_carlo.py # simulation statistical tests
```

---

## Setup

```bash
git clone <repo-url>
cd LP-app
python -m venv venv
source venv/bin/activate
pip install pulp pyyaml numpy scipy rich pytest
```

---

## Usage

**Run the full planning report:**
```bash
python cli.py
```

**Custom menu file:**
```bash
python cli.py --menu data/menu.yaml
```

**Reproducible results:**
```bash
python cli.py --seed 42
```

**Pin a drink to a specific quantity and log why:**
```bash
python cli.py --override "Iced White Mocha=15" --reason "group booking"
```

**Multiple overrides:**
```bash
python cli.py \
  --override "Iced White Mocha=15" --reason "group booking" \
  --override "Iced Strawberry Matcha Latte=10" --reason "promotional event"
```

**Run the solver or simulation on their own:**
```bash
python -m solver.model          # deterministic solve only
python -m solver.monte_carlo    # simulation only
```

**Run tests:**
```bash
python -m pytest tests/ -v
```

---

## Configuring the menu

Everything lives in `data/menu.yaml`. Edit it to match your cafe's actual menu:

```yaml
products:
  - name: Iced Strawberry Matcha Latte
    unit_cost: 2.60        # ingredient cost per cup (AUD)
    unit_price: 11.00      # selling price (AUD)
    prep_time_min: 4       # barista prep time per cup
    is_integer: true       # whole units only
    demand_low: 5          # minimum realistic daily demand
    demand_expected: 15    # most likely daily demand
    demand_high: 30        # maximum realistic daily demand

constraints:
  daily_budget: 150.00     # max ingredient spend per day (AUD)
  daily_labor_min: 480     # total prep minutes available (8 hours)
  min_quantity_per_product: 5
  max_quantity_per_product: 50
```

For demand, you only need to provide three numbers: your lowest expected day, your typical day, and your busiest day. The tool fits a triangular distribution from those and handles the rest.

---

## How the optimiser works

The solver maximises total daily profit:

```
profit = sum of (unit_price - unit_cost) x quantity  for each product
```

Subject to:
- Total ingredient cost must stay within the daily budget
- Total prep time must stay within available labor hours
- Each quantity must be between the configured min and max
- Each quantity cannot exceed sampled demand (Monte Carlo runs only)

In Monte Carlo mode, demand is randomly sampled from each product's triangular distribution. The LP runs 2,000 times and the results are aggregated into percentile-based recommendations with a confidence flag.

---

## Assumptions and data sources

| Field | Source |
|---|---|
| `unit_price` | Sourced from real cafe menu prices |
| `unit_cost` | Estimated from Australian wholesale ingredient benchmarks |
| `demand_*` | Estimated from comparable small cafe benchmarks, to be replaced with real sales data |
| `prep_time_min` | Estimated from standard cafe preparation times |

---

## Confidence flags

A drink is flagged LOW confidence when its recommended quantity varies by more than 50% of the median across simulations:

```
(95th percentile - 5th percentile) / median > 0.50
```

This means the recommendation is sensitive to demand uncertainty and should be treated with caution until better data is available.

---

## Roadmap

- [ ] Phase 4: backtesting against real sales data with a significance test vs. a naive baseline
- [ ] Phase 6: Streamlit web interface with what-if sliders and saved scenarios
- [ ] Multi-period model: ingredient carryover across days with shelf-life constraints
