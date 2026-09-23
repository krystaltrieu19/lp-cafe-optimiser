import pytest
from solver.monte_carlo import run


BASE_MENU = {
    "products": [
        {
            "name": "Drink A",
            "unit_cost": 2.00,
            "unit_price": 9.00,
            "prep_time_min": 2,
            "is_integer": True,
            "demand_low": 10,
            "demand_expected": 20,
            "demand_high": 30,
        },
        {
            "name": "Drink B",
            "unit_cost": 3.00,
            "unit_price": 10.00,
            "prep_time_min": 3,
            "is_integer": True,
            "demand_low": 5,
            "demand_expected": 15,
            "demand_high": 25,
        },
    ],
    "constraints": {
        "daily_budget": 100.00,
        "daily_labor_min": 120,
        "min_quantity_per_product": 0,
        "max_quantity_per_product": 50,
    },
}


def test_reproducibility():
    # Same seed must produce identical results every time
    result_1 = run(BASE_MENU, n=500, seed=42)
    result_2 = run(BASE_MENU, n=500, seed=42)
    assert result_1["profit"] == result_2["profit"]
    assert result_1["products"] == result_2["products"]



def test_profit_interval_ordering():
    result = run(BASE_MENU, n=500, seed=42)
    p = result["profit"]
    assert p["p5"] <= p["median"] <= p["p95"]


def test_qty_interval_ordering():
    result = run(BASE_MENU, n=500, seed=42)
    for product in result["products"]:
        assert product["p5_qty"] <= product["median_qty"] <= product["p95_qty"]


def test_n_solved_leq_n_simulations():
    result = run(BASE_MENU, n=200, seed=42)
    assert result["n_solved"] <= result["n_simulations"]
    assert result["n_solved"] > 0


def test_high_demand_all_runs_solve():
    # When demand is always far above max_quantity, every run should be feasible
    menu = {
        "products": [
            {
                "name": "Drink A",
                "unit_cost": 1.00,
                "unit_price": 5.00,
                "prep_time_min": 1,
                "is_integer": True,
                "demand_low": 100,
                "demand_expected": 150,
                "demand_high": 200,
            },
        ],
        "constraints": {
            "daily_budget": 50.00,
            "daily_labor_min": 60,
            "min_quantity_per_product": 0,
            "max_quantity_per_product": 40,
        },
    }
    result = run(menu, n=200, seed=42)
    assert result["n_solved"] == result["n_simulations"]


def test_low_confidence_flag_wide_demand():
    # A product with a very wide demand range should be flagged low confidence
    menu = {
        "products": [
            {
                "name": "Volatile Drink",
                "unit_cost": 1.00,
                "unit_price": 5.00,
                "prep_time_min": 1,
                "is_integer": True,
                "demand_low": 1,
                "demand_expected": 25,
                "demand_high": 50,
            },
        ],
        "constraints": {
            "daily_budget": 200.00,
            "daily_labor_min": 200,
            "min_quantity_per_product": 0,
            "max_quantity_per_product": 50,
        },
    }
    result = run(menu, n=1000, seed=42)
    volatile = result["products"][0]
    assert volatile["low_confidence"] is True


def test_high_confidence_flag_narrow_demand():
    # A product with a very narrow demand range should NOT be flagged
    menu = {
        "products": [
            {
                "name": "Stable Drink",
                "unit_cost": 1.00,
                "unit_price": 5.00,
                "prep_time_min": 1,
                "is_integer": True,
                "demand_low": 19,
                "demand_expected": 20,
                "demand_high": 21,
            },
        ],
        "constraints": {
            "daily_budget": 200.00,
            "daily_labor_min": 200,
            "min_quantity_per_product": 0,
            "max_quantity_per_product": 50,
        },
    }
    result = run(menu, n=1000, seed=42)
    stable = result["products"][0]
    assert stable["low_confidence"] is False


def test_output_has_all_products():
    result = run(BASE_MENU, n=200, seed=42)
    names = [p["name"] for p in result["products"]]
    assert "Drink A" in names
    assert "Drink B" in names
