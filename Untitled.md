---
title: LP/ILP Cafe Planning App
created: 2026-09-22
tags: [project, cafe, optimization, lp-app]
status: planning
---

# LP/ILP Cafe Planning App — Build Checklist

## Phase 1: Core deterministic solver
- [ ] Pick solver library (PuLP or OR-Tools) and install
- [ ] Define product data structure: name, unit cost, unit price, resource usage per unit (storage, prep time, ingredient qty)
- [ ] Build objective function: maximize sum of (price - cost) * quantity
- [ ] Implement constraint types: budget, storage capacity, prep/labor hours, per-product min/max
- [ ] Add integer vs. continuous toggle per product
- [ ] Solve a hand-verifiable toy problem (2-3 products, 1-2 constraints) and confirm solver output matches your manual calculation
- [ ] Build out your real 5-drink [[DOT Cafe|DOT°]] menu as the first real test case, with best-estimate costs/prices
- [ ] Add infeasibility handling: detect and clearly report when constraints can't all be satisfied (don't crash, don't return garbage)

## Phase 2: Statistical validation layer (this is what makes it "reliable")
- [ ] For each product, replace single-point demand with a distribution (start simple: triangular(low, expected, high) or normal(mean, std))
- [ ] Build Monte Carlo wrapper: sample demand from distributions, solve LP, record result, repeat N times (start with N=1000-5000)
- [ ] From the simulation runs, compute and report: median recommended quantity per product, 90% interval (5th-95th percentile), median profit and its interval
- [ ] Extract LP shadow prices / ranging info from each solve and report which constraints are binding most often across simulations
- [ ] Write a "confidence" rule: if a product's recommended quantity varies by more than X% across the simulation range, flag it as low-confidence
- [ ] Document your assumed distributions and their sources (comparable-business benchmarks, your own estimates) so every output is traceable to an assumption, not just a number

## Phase 3: Test suite
- [ ] Unit tests: model construction (right coefficients, right constraint matrix) independent of solver
- [ ] Unit tests: solver wrapper against known small hand-solved problems
- [ ] Edge case tests: infeasible input, zero budget, single product, missing constraint (unbounded)
- [ ] Input validation tests: negative price/cost, wrong type where integer required, missing fields
- [ ] Regression test: fixed scenario (your 5-drink menu) with a locked expected output, re-run on every code change
- [ ] Monotonicity test: loosening any constraint must never decrease optimal profit (property test across randomized scenarios)
- [ ] Monte Carlo reproducibility test: same random seed produces same distribution of results

## Phase 4: Backtesting & significance testing (once ANY real or pilot data exists)
- [ ] Build a naive baseline (e.g. stock proportional to prior period's sales) to compare against
- [ ] Backtest LP recommendation vs. naive baseline over available historical/pilot periods
- [ ] Run paired significance test (paired t-test or bootstrap CI) on profit difference between LP and naive baseline
- [ ] Only claim "statistically validated" once LP beats baseline with a real confidence interval, not just on average

## Phase 5: Minimal usable interface (still not a web app)
- [ ] Command-line or notebook interface: input products/constraints via a simple config file (YAML/CSV)
- [ ] Output: plain-text or simple table summary — recommended quantities, profit interval, binding constraints, confidence flags
- [ ] Manual override field: let yourself adjust a quantity and log why

## Phase 6 (later, not now): web app
- [ ] Form-based input UI
- [ ] What-if sliders
- [ ] Multi-business / saved-scenario support

## Notes
- Phases 2-3 should run alongside Phase 1, not strictly after — write the regression test the moment the first solve works.
- Phase 4 isn't a blocker — Phase 5 can ship using benchmark-based distributions as long as every output carries a confidence label.