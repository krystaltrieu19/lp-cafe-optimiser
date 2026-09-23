import argparse
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import box
from rich.rule import Rule
from rich.text import Text

from solver.model import load_menu, build_and_solve
from solver.monte_carlo import run as monte_carlo_run

console = Console()


def parse_overrides(override_args: list[str]) -> dict[str, dict]:
    """Parse --override 'Drink Name=qty' --reason 'why' pairs."""
    overrides = {}
    for entry in override_args:
        if "=" not in entry:
            console.print(f"[red]Invalid override format: '{entry}'. Use 'Drink Name=qty'[/red]")
            continue
        name, qty_str = entry.rsplit("=", 1)
        try:
            overrides[name.strip()] = {"qty": int(qty_str.strip()), "reason": ""}
        except ValueError:
            console.print(f"[red]Override quantity must be an integer: '{qty_str}'[/red]")
    return overrides


def apply_override_reasons(overrides: dict, reasons: list[str]) -> None:
    names = list(overrides.keys())
    for i, reason in enumerate(reasons):
        if i < len(names):
            overrides[names[i]]["reason"] = reason


def apply_overrides_to_menu(menu: dict, overrides: dict) -> dict:
    """Fix overridden products to exact quantities by setting min=max=qty."""
    import copy
    menu = copy.deepcopy(menu)
    for product in menu["products"]:
        if product["name"] in overrides:
            qty = overrides[product["name"]]["qty"]
            product["_override_qty"] = qty
    return menu


def build_and_solve_with_overrides(menu: dict, overrides: dict) -> dict:
    """Re-solve LP with overridden products pinned to their specified quantities."""
    import pulp
    import copy

    products = menu["products"]
    constraints = menu["constraints"]

    prob = pulp.LpProblem("cafe_profit_maximisation", pulp.LpMaximize)

    qty = {}
    for p in products:
        name = p["name"]
        if name in overrides:
            fixed = overrides[name]["qty"]
            lo, hi = fixed, fixed
        else:
            lo = constraints["min_quantity_per_product"]
            hi = constraints["max_quantity_per_product"]

        cat = "Integer" if p["is_integer"] else "Continuous"
        qty[name] = pulp.LpVariable(name.replace(" ", "_"), lowBound=lo, upBound=hi, cat=cat)

    prob += pulp.lpSum(
        (p["unit_price"] - p["unit_cost"]) * qty[p["name"]] for p in products
    )

    prob += (
        pulp.lpSum(p["unit_cost"] * qty[p["name"]] for p in products)
        <= constraints["daily_budget"]
    )
    prob += (
        pulp.lpSum(p["prep_time_min"] * qty[p["name"]] for p in products)
        <= constraints["daily_labor_min"]
    )

    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    status = pulp.LpStatus[prob.status]

    if status != "Optimal":
        return {"status": status, "products": [], "total_profit": None}

    results = []
    for p in products:
        results.append({
            "name": p["name"],
            "quantity": int(qty[p["name"]].value()),
            "unit_profit": round(p["unit_price"] - p["unit_cost"], 2),
            "total_contribution": round(
                (p["unit_price"] - p["unit_cost"]) * qty[p["name"]].value(), 2
            ),
        })

    total_cost = round(sum(p["unit_cost"] * qty[p["name"]].value() for p in products), 2)
    total_labor = round(sum(p["prep_time_min"] * qty[p["name"]].value() for p in products), 2)

    return {
        "status": status,
        "products": results,
        "total_profit": round(pulp.value(prob.objective), 2),
        "total_cost": total_cost,
        "total_labor_min": total_labor,
        "budget_used_pct": round(total_cost / constraints["daily_budget"] * 100, 1),
        "labor_used_pct": round(total_labor / constraints["daily_labor_min"] * 100, 1),
    }


def print_report(det: dict, mc: dict, menu: dict, overrides: dict) -> None:
    constraints = menu["constraints"]
    mc_by_name = {p["name"]: p for p in mc["products"]}

    console.print()
    console.rule("[bold cyan]DOT° Cafe — Daily Planning Report[/bold cyan]")
    console.print()

    # Recommendations table
    table = Table(
        title="Recommendations",
        box=box.SIMPLE_HEAD,
        show_lines=False,
        title_style="bold",
    )
    table.add_column("Drink", style="white", min_width=38)
    table.add_column("Rec Qty", justify="right")
    table.add_column("90% Range", justify="center")
    table.add_column("Unit Profit", justify="right")
    table.add_column("Confidence", justify="center")

    for p in det["products"]:
        name = p["name"]
        mc_p = mc_by_name.get(name)
        is_override = name in overrides

        qty_display = str(p["quantity"])
        if is_override:
            qty_display = f"{p['quantity']} [dim](override)[/dim]"

        if mc_p:
            range_str = f"{mc_p['p5_qty']} – {mc_p['p95_qty']}"
            confidence = "[yellow]⚠ LOW[/yellow]" if mc_p["low_confidence"] else "[green]OK[/green]"
        else:
            range_str = "—"
            confidence = "—"

        table.add_row(
            name,
            qty_display,
            range_str,
            f"${p['unit_profit']:.2f}",
            confidence,
        )

    console.print(table)

    # Profit forecast
    p = mc["profit"]
    console.print(f"  [bold]Profit Forecast[/bold]")
    console.print(f"    Median:       [green]${p['median']:,.2f}[/green]")
    console.print(f"    90% interval: ${p['p5']:,.2f} – ${p['p95']:,.2f}")
    console.print(f"    Deterministic ceiling: [dim]${det['total_profit']:,.2f}[/dim]")
    console.print()

    # Constraints
    budget_pct = det["budget_used_pct"]
    labor_pct = det["labor_used_pct"]
    budget_color = "red" if budget_pct >= 95 else "yellow" if budget_pct >= 80 else "green"
    labor_color = "red" if labor_pct >= 95 else "yellow" if labor_pct >= 80 else "green"

    console.print(f"  [bold]Constraints[/bold]")
    console.print(
        f"    Budget:  ${det['total_cost']:.2f} / ${constraints['daily_budget']:.2f}  "
        f"[{budget_color}]({budget_pct}%)[/{budget_color}]"
        + (" [bold red]← bottleneck[/bold red]" if budget_pct >= 95 else "")
    )
    console.print(
        f"    Labor:   {det['total_labor_min']:.0f} min / {constraints['daily_labor_min']} min  "
        f"[{labor_color}]({labor_pct}%)[/{labor_color}]"
        + (" [bold red]← bottleneck[/bold red]" if labor_pct >= 95 else "")
    )
    console.print()

    # Overrides
    if overrides:
        console.print(f"  [bold]Overrides Applied[/bold]")
        for name, ov in overrides.items():
            reason = f" — {ov['reason']}" if ov["reason"] else ""
            console.print(f"    • {name}: set to [yellow]{ov['qty']}[/yellow]{reason}")
        console.print()

    # MC metadata
    console.print(
        f"  [dim]Monte Carlo: {mc['n_solved']}/{mc['n_simulations']} runs solved[/dim]"
    )
    console.print()


def main():
    parser = argparse.ArgumentParser(description="DOT° Cafe LP Planning Tool")
    parser.add_argument(
        "--menu",
        default="data/menu.yaml",
        help="Path to menu YAML file (default: data/menu.yaml)",
    )
    parser.add_argument(
        "--runs", type=int, default=2000, help="Monte Carlo simulation runs (default: 2000)"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--override",
        action="append",
        default=[],
        metavar="'Drink Name=qty'",
        help="Pin a drink to a specific quantity, e.g. --override 'Iced White Mocha=10'",
    )
    parser.add_argument(
        "--reason",
        action="append",
        default=[],
        metavar="'why'",
        help="Reason for the override (matched in order to --override flags)",
    )

    args = parser.parse_args()
    menu_path = Path(args.menu)

    if not menu_path.exists():
        console.print(f"[red]Menu file not found: {menu_path}[/red]")
        return

    menu = load_menu(menu_path)
    overrides = parse_overrides(args.override)
    apply_override_reasons(overrides, args.reason)

    console.print(f"\n[dim]Loading menu from {menu_path}...[/dim]")
    console.print(f"[dim]Running {args.runs} Monte Carlo simulations...[/dim]")

    if overrides:
        det = build_and_solve_with_overrides(menu, overrides)
    else:
        det = build_and_solve(menu)

    mc = monte_carlo_run(menu, n=args.runs, seed=args.seed)

    print_report(det, mc, menu, overrides)


if __name__ == "__main__":
    main()
