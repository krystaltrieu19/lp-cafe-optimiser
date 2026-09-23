import numpy as np
from scipy.stats import triang
from solver.model import build_and_solve

CONFIDENCE_FLAG_THRESHOLD = 0.50  # flag if (p95-p5)/median > 50%


def _sample_demand(products: list, rng: np.random.Generator) -> dict:
    caps = {}
    for p in products:
        lo, mid, hi = p["demand_low"], p["demand_expected"], p["demand_high"]
        # scipy triangular: c = (mode - low) / (high - low)
        c = (mid - lo) / (hi - lo)
        sample = triang.rvs(c, loc=lo, scale=(hi - lo), random_state=rng)
        caps[p["name"]] = max(0, int(round(sample)))
    return caps


def run(menu: dict, n: int = 2000, seed: int | None = None) -> dict:
    rng = np.random.default_rng(seed)
    products = menu["products"]
    product_names = [p["name"] for p in products]

    qty_records = {name: [] for name in product_names}
    profit_records = []

    for _ in range(n):
        demand_caps = _sample_demand(products, rng)
        result = build_and_solve(menu, demand_caps=demand_caps)

        if result["status"] != "Optimal":
            continue

        profit_records.append(result["total_profit"])
        for p in result["products"]:
            qty_records[p["name"]].append(p["quantity"])

    solved = len(profit_records)

    product_stats = []
    for name in product_names:
        qtys = np.array(qty_records[name])
        if len(qtys) == 0:
            continue

        median = float(np.median(qtys))
        p5 = float(np.percentile(qtys, 5))
        p95 = float(np.percentile(qtys, 95))

        if median > 0:
            low_confidence = (p95 - p5) / median > CONFIDENCE_FLAG_THRESHOLD
        else:
            low_confidence = True

        product_stats.append({
            "name": name,
            "median_qty": round(median),
            "p5_qty": round(p5),
            "p95_qty": round(p95),
            "low_confidence": low_confidence,
        })

    profits = np.array(profit_records)
    profit_stats = {
        "median": round(float(np.median(profits)), 2),
        "p5": round(float(np.percentile(profits, 5)), 2),
        "p95": round(float(np.percentile(profits, 95)), 2),
    }

    return {
        "n_simulations": n,
        "n_solved": solved,
        "products": product_stats,
        "profit": profit_stats,
    }


def _print_results(result: dict) -> None:
    print(f"\nMonte Carlo Results  ({result['n_solved']}/{result['n_simulations']} runs solved)\n")

    print(f"{'Drink':<40} {'Med Qty':>8} {'5th':>6} {'95th':>6} {'Flag':>6}")
    print("-" * 72)
    for p in result["products"]:
        flag = "⚠ LOW" if p["low_confidence"] else "OK"
        print(
            f"{p['name']:<40} {p['median_qty']:>8} {p['p5_qty']:>6} {p['p95_qty']:>6} {flag:>6}"
        )

    p = result["profit"]
    print("-" * 72)
    print(f"\nProfit  median: ${p['median']:,.2f}   90% interval: [${p['p5']:,.2f} – ${p['p95']:,.2f}]")


if __name__ == "__main__":
    from pathlib import Path
    from solver.model import load_menu

    menu_path = Path(__file__).parent.parent / "data" / "menu.yaml"
    menu = load_menu(menu_path)
    result = run(menu, n=2000, seed=42)
    _print_results(result)
