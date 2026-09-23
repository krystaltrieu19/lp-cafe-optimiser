import pulp
import yaml
from pathlib import Path


def load_menu(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def build_and_solve(menu: dict, demand_caps: dict | None = None) -> dict:
    products = menu["products"]
    constraints = menu["constraints"]

    prob = pulp.LpProblem("cafe_profit_maximisation", pulp.LpMaximize)

    # Decision variables: how many units of each product to make
    qty = {}
    for p in products:
        name = p["name"]
        if p["is_integer"]:
            qty[name] = pulp.LpVariable(
                name.replace(" ", "_"),
                lowBound=constraints["min_quantity_per_product"],
                upBound=constraints["max_quantity_per_product"],
                cat="Integer",
            )
        else:
            qty[name] = pulp.LpVariable(
                name.replace(" ", "_"),
                lowBound=constraints["min_quantity_per_product"],
                upBound=constraints["max_quantity_per_product"],
                cat="Continuous",
            )

    # Objective: maximise total profit (price - cost) * quantity
    prob += pulp.lpSum(
        (p["unit_price"] - p["unit_cost"]) * qty[p["name"]] for p in products
    ), "total_profit"

    # Demand caps: can't make more than customers will buy
    if demand_caps:
        for p in products:
            name = p["name"]
            if name in demand_caps:
                prob += qty[name] <= demand_caps[name], f"demand_{name.replace(' ', '_')}"

    # Constraint 1: ingredient budget
    prob += (
        pulp.lpSum(p["unit_cost"] * qty[p["name"]] for p in products)
        <= constraints["daily_budget"],
        "budget",
    )

    # Constraint 2: total prep time
    prob += (
        pulp.lpSum(p["prep_time_min"] * qty[p["name"]] for p in products)
        <= constraints["daily_labor_min"],
        "labor",
    )

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    status = pulp.LpStatus[prob.status]

    if status != "Optimal":
        return {"status": status, "products": [], "total_profit": None}

    results = []
    for p in products:
        results.append(
            {
                "name": p["name"],
                "quantity": int(qty[p["name"]].value()),
                "unit_profit": round(p["unit_price"] - p["unit_cost"], 2),
                "total_contribution": round(
                    (p["unit_price"] - p["unit_cost"]) * qty[p["name"]].value(), 2
                ),
            }
        )

    total_profit = round(pulp.value(prob.objective), 2)
    total_cost = round(sum(p["unit_cost"] * qty[p["name"]].value() for p in products), 2)
    total_labor = round(sum(p["prep_time_min"] * qty[p["name"]].value() for p in products), 2)

    return {
        "status": status,
        "products": results,
        "total_profit": total_profit,
        "total_cost": total_cost,
        "total_labor_min": total_labor,
        "budget_used_pct": round(total_cost / constraints["daily_budget"] * 100, 1),
        "labor_used_pct": round(total_labor / constraints["daily_labor_min"] * 100, 1),
    }


if __name__ == "__main__":
    menu_path = Path(__file__).parent.parent / "data" / "menu.yaml"
    menu = load_menu(menu_path)
    result = build_and_solve(menu)

    print(f"\nStatus: {result['status']}")
    print(f"{'Drink':<40} {'Qty':>5} {'Unit Profit':>12} {'Contribution':>14}")
    print("-" * 75)
    for p in result["products"]:
        print(f"{p['name']:<40} {p['quantity']:>5} ${p['unit_profit']:>11.2f} ${p['total_contribution']:>13.2f}")
    print("-" * 75)
    print(f"{'Total Profit':.<40} ${result['total_profit']:>13.2f}")
    print(f"\nBudget used:  ${result['total_cost']:.2f} / {result['budget_used_pct']}%")
    print(f"Labor used:   {result['total_labor_min']:.0f} min / {result['labor_used_pct']}%")
