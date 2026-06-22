from .graph import estimate_actual_cost


def _state(hotels, restaurants, budget=20000, days=3, adults=2, children=0):
    return {
        "budget": budget,
        "days": days,
        "adults": adults,
        "children": children,
        "hotels": hotels,
        "restaurants": restaurants,
        "cost_breakdown": {
            "accommodation": round(budget * 0.35),
            "food": round(budget * 0.25),
            "transport": round(budget * 0.15),
            "attractions": round(budget * 0.10),
            "buffer": round(budget * 0.15),
        },
    }


def test_flags_hotel_far_over_budget():
    state = _state(
        hotels=[{"price_per_night": 15000}],
        restaurants=[{"cost_for_two_inr": 600}],
        budget=2000,
        days=1,
        adults=2,
    )
    actual = estimate_actual_cost(state)
    assert actual["total_actual"] > round(state["budget"] * 1.2)


def test_within_budget_not_flagged():
    state = _state(
        hotels=[{"price_per_night": 2000}],
        restaurants=[{"cost_for_two_inr": 500}],
        budget=20000,
        days=3,
        adults=2,
    )
    actual = estimate_actual_cost(state)
    low, high = round(state["budget"] * 0.8), round(state["budget"] * 1.2)
    assert low <= actual["total_actual"] <= high


def test_falls_back_to_planned_budget_when_price_unparseable():
    state = _state(hotels=[{"price_per_night": "N/A"}], restaurants=[{"cost_for_two_inr": "N/A"}])
    actual = estimate_actual_cost(state)
    assert actual["accommodation_actual"] == state["cost_breakdown"]["accommodation"]
    assert actual["food_actual"] == state["cost_breakdown"]["food"]
