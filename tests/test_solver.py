import pytest
from solver.model import build_and_solve


TOY_MENU = {
    "products": [
        {
            "name": "Drink A",
            "unit_cost": 3.00,
            "unit_price": 10.00,  # profit = $7, expensive to make, fast to prep
            "prep_time_min": 2,
            "is_integer": True,
        },
        {
            "name": "Drink B",
            "unit_cost": 2.00,
            "unit_price": 8.00,   # profit = $6, cheap to make, slow to prep
            "prep_time_min": 4,
            "is_integer": True,
        },
    ],
    "constraints": {
        "daily_budget": 18.00,
        "daily_labor_min": 20,
        "min_quantity_per_product": 0,
        "max_quantity_per_product": 10,
    },
}


def test_toy_problem_optimal_status():
    result = build_and_solve(TOY_MENU)
    assert result["status"] == "Optimal"


def test_toy_problem_quantities():
    # Hand-solved: both constraints bind at A=4, B=3
    # Drink A: profit=$7, cost=$3, prep=2min  (fast but expensive)
    # Drink B: profit=$6, cost=$2, prep=4min  (slow but cheap)
    # Budget:  3(4) + 2(3) = 18
    # Labor:   2(4) + 4(3) = 20 
    # Profit:  7(4) + 6(3) = 46 
    # Budget forces fewer A; labor forces fewer B; both bind together
    result = build_and_solve(TOY_MENU)
    qty = {p["name"]: p["quantity"] for p in result["products"]}
    assert qty["Drink A"] == 4
    assert qty["Drink B"] == 3


def test_toy_problem_profit():
    result = build_and_solve(TOY_MENU)
    assert result["total_profit"] == pytest.approx(46.00)


def test_infeasible_budget():
    # Budget of $1 can't satisfy min_quantity=1 for any product (cheapest costs $2)
    infeasible_menu = {
        "products": TOY_MENU["products"],
        "constraints": {
            "daily_budget": 1.00,
            "daily_labor_min": 999,
            "min_quantity_per_product": 1,
            "max_quantity_per_product": 10,
        },
    }
    result = build_and_solve(infeasible_menu)
    assert result["status"] != "Optimal"
    assert result["total_profit"] is None
