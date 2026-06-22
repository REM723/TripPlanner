import json
import re
from datetime import date
from typing import List, Optional, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from .llm import get_llm
from .weather import fetch_forecast

SUGGESTED_DESTINATIONS = ["Munnar", "Wayanad", "Coorg", "Goa", "Manali", "Udaipur"]


class PlannerState(TypedDict):
    budget: int
    adults: int
    children: int
    days: int
    preferences: List[str]
    destination: Optional[str]
    hotel_type: str
    food_preferences: List[str]
    starting_city: Optional[str]
    must_visit_places: List[str]
    mobility_constraints: Optional[str]
    start_date: Optional[str]
    language: str

    input_valid: bool
    validation_errors: List[str]

    destination_was_suggested: bool
    suggested_destinations: List[str]

    cost_breakdown: dict
    budget_status: str
    budget_message: str
    minimum_viable_budget: Optional[int]

    hotels: list
    restaurants: List[dict]
    attractions: List[str]
    optional_inclusions: List[dict]
    why_this_fits: str

    itinerary: List[dict]
    weather: List[dict]


MIN_PER_DAY_PER_PERSON = 1200
MAX_PER_DAY_PER_PERSON = 6000


itinerary_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
        You are an expert AI Travel Planner.

        Create a realistic, budget-aware, day-by-day itinerary covering the
        full trip duration. Respect any mobility constraints and prioritize
        any must-visit places.

        If a weather forecast is given for a day, plan around it: swap outdoor
        sightseeing for indoor/covered options (museums, malls, cafes, indoor
        markets) on days marked rain_likely, and favor outdoor activities on
        clear days.

        Write all text values (morning/afternoon/evening/meals) in {language}.
        Keep the JSON keys themselves in English exactly as shown below.

        Return ONLY a JSON list with this exact structure, one entry per day:

        [
          {{
            "day": 1,
            "morning": "What to do in the morning, one or two sentences",
            "afternoon": "What to do in the afternoon, one or two sentences",
            "evening": "What to do in the evening, one or two sentences",
            "meals": {{
              "breakfast": "Where/what to eat",
              "lunch": "Where/what to eat",
              "dinner": "Where/what to eat"
            }}
          }}
        ]

        Return nothing else. No explanation. Just the JSON list.
        """,
        ),
        (
            "human",
            """
        Trip Details

        Budget: Rs.{budget}

        Adults: {adults}

        Children: {children}

        Number of Days: {days}

        Starting City: {starting_city}

        Destination: {destination}

        Sightseeing Preferences:
        {preferences}

        Hotel Type:
        {hotel_type}

        Food Preferences:
        {food_preferences}

        Must-Visit Places:
        {must_visit_places}

        Mobility Constraints:
        {mobility_constraints}

        Cost Breakdown:
        {cost_breakdown}

        Restaurants already chosen for meals (reference these by name where relevant):
        {restaurant_names}

        Weather Forecast (one line per day, may be empty if unavailable):
        {weather_forecast}

        Create the day-by-day itinerary JSON now, written in {language}.
        """,
        ),
    ]
)

hotel_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
        You are a travel expert. Recommend exactly 3 real hotels for the given destination.

        Rules:
        - Match the hotel type (Budget / Standard / Luxury)
        - Stay within the accommodation budget
        - Write "highlights" in {language}. Keep "name", "type" and JSON keys in English.
        - Return ONLY a JSON list with this structure:

        [
          {{
            "name": "Hotel Name",
            "type": "Budget/Standard/Luxury",
            "price_per_night": 1500,
            "highlights": "Key features in one line",
            "address": "Area, City"
          }}
        ]

        Return nothing else. No explanation. Just the JSON list.
        """,
        ),
        (
            "human",
            """
        Destination: {destination}
        Hotel Type: {hotel_type}
        Accommodation Budget: Rs.{accommodation_budget}
        Number of Days: {days}
        Language: {language}
        {feedback}
        """,
        ),
    ]
)


restaurant_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
        You are a travel expert. Recommend exactly 3 real restaurants for the given destination.

        Rules:
        - Respect the stated food preferences
        - Note group/family suitability based on the traveler mix
        - Stay within a reasonable per-meal cost for the stated food budget
        - Write "cuisine" and "group_suitability" in {language}. Keep "name" and JSON keys in English.
        - Return ONLY a JSON list with this structure:

        [
          {{
            "name": "Restaurant Name",
            "cost_for_two_inr": 600,
            "location": "Area, City",
            "cuisine": "Cuisine type",
            "rating": 4.2,
            "group_suitability": "One-line note, e.g. Family-friendly"
          }}
        ]

        Return nothing else. No explanation. Just the JSON list.
        """,
        ),
        (
            "human",
            """
        Destination: {destination}
        Food Preferences: {food_preferences}
        Food Budget (for the whole trip): Rs.{food_budget}
        Number of Days: {days}
        Adults: {adults}
        Children: {children}
        Language: {language}
        {feedback}
        """,
        ),
    ]
)


def validate_inputs(state: PlannerState) -> PlannerState:
    errors = []

    if state["budget"] <= 0:
        errors.append("Budget must be greater than 0")
    if state["days"] <= 0:
        errors.append("Days must be greater than 0")
    if state["adults"] < 1:
        errors.append("At least one adult is required")
    if state["children"] < 0:
        errors.append("Children cannot be negative")

    return {**state, "input_valid": len(errors) == 0, "validation_errors": errors}


def destination_router(state: PlannerState) -> str:
    if not state["input_valid"]:
        return "invalid"
    if not state.get("destination"):
        return "suggest"
    return "continue"


def suggest_destinations(state: PlannerState) -> PlannerState:
    chosen = SUGGESTED_DESTINATIONS[0]

    for pref in state.get("preferences", []):
        for place in SUGGESTED_DESTINATIONS:
            if pref.strip().lower() in place.lower():
                chosen = place
                break

    return {
        **state,
        "destination": chosen,
        "destination_was_suggested": True,
        "suggested_destinations": SUGGESTED_DESTINATIONS,
    }


def budget_allocator(state: PlannerState) -> PlannerState:
    budget = state["budget"]

    breakdown = {
        "accommodation": round(budget * 0.35, 2),
        "food": round(budget * 0.25, 2),
        "transport": round(budget * 0.15, 2),
        "attractions": round(budget * 0.10, 2),
        "buffer": round(budget * 0.15, 2),
        "total": budget,
        "target_range_inr": [round(budget * 0.8), round(budget * 1.2)],
    }

    return {**state, "cost_breakdown": breakdown}


def budget_feasibility(state: PlannerState) -> PlannerState:
    days = state["days"]
    people = state["adults"] + state["children"]
    per_day_per_person = state["budget"] / days / people

    if per_day_per_person < MIN_PER_DAY_PER_PERSON:
        minimum_viable = round(MIN_PER_DAY_PER_PERSON * days * people)
        return {
            **state,
            "budget_status": "too_low",
            "minimum_viable_budget": minimum_viable,
            "budget_message": (
                f"Rs.{state['budget']} isn't enough for a basic {days}-day trip to "
                f"{state.get('destination') or 'this destination'} for {people} people. "
                f"You'll likely need at least Rs.{minimum_viable}."
            ),
        }

    if per_day_per_person > MAX_PER_DAY_PER_PERSON and state["hotel_type"] != "Luxury":
        return {
            **state,
            "budget_status": "too_high",
            "budget_message": (
                f"Rs.{state['budget']} is well above what a {days}-day trip to "
                f"{state.get('destination') or 'this destination'} for {people} people typically needs. "
                "Lower the budget or upgrade the experience for better hotels and more paid attractions."
            ),
        }

    return {**state, "budget_status": "feasible", "budget_message": ""}


def feasibility_router(state: PlannerState) -> str:
    return state["budget_status"]


def _select_hotels(state: PlannerState, feedback: str = "") -> list:
    llm = get_llm()
    accommodation_budget = state["cost_breakdown"].get("accommodation", 5000)

    prompt = hotel_prompt.invoke(
        {
            "destination": state["destination"],
            "hotel_type": state["hotel_type"],
            "accommodation_budget": accommodation_budget,
            "days": state["days"],
            "language": state.get("language") or "English",
            "feedback": feedback,
        }
    )

    response = llm.invoke(prompt)
    raw = re.sub(r"```json|```", "", response.content.strip()).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return [
            {
                "name": raw,
                "type": state["hotel_type"],
                "price_per_night": "N/A",
                "highlights": "",
                "address": "",
            }
        ]


def select_hotels(state: PlannerState) -> PlannerState:
    return {**state, "hotels": _select_hotels(state)}


def _select_restaurants(state: PlannerState, feedback: str = "") -> list:
    llm = get_llm()
    food_budget = state["cost_breakdown"].get("food", 3000)

    prompt = restaurant_prompt.invoke(
        {
            "destination": state["destination"],
            "food_preferences": ", ".join(state["food_preferences"]) or "No specific preference",
            "food_budget": food_budget,
            "days": state["days"],
            "adults": state["adults"],
            "children": state["children"],
            "language": state.get("language") or "English",
            "feedback": feedback,
        }
    )

    response = llm.invoke(prompt)
    raw = re.sub(r"```json|```", "", response.content.strip()).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return [
            {
                "name": raw,
                "cost_for_two_inr": 0,
                "location": state["destination"],
                "cuisine": "N/A",
                "rating": 0,
                "group_suitability": "N/A",
            }
        ]


def select_restaurants(state: PlannerState) -> PlannerState:
    return {**state, "restaurants": _select_restaurants(state)}


def _cheapest(items: list, key: str) -> Optional[float]:
    prices = [item[key] for item in items if isinstance(item.get(key), (int, float))]
    return min(prices) if prices else None


def estimate_actual_cost(state: PlannerState) -> dict:
    """Best-effort actual cost from the cheapest generated hotel/restaurant (spec §6.1)."""
    cost_breakdown = state["cost_breakdown"]
    days = state["days"]
    people = state["adults"] + state["children"]

    cheapest_hotel = _cheapest(state["hotels"], "price_per_night")
    accommodation_actual = cheapest_hotel * days if cheapest_hotel is not None else cost_breakdown["accommodation"]

    cheapest_meal = _cheapest(state["restaurants"], "cost_for_two_inr")
    food_actual = cheapest_meal / 2 * people * 3 * days if cheapest_meal is not None else cost_breakdown["food"]

    total_actual = (
        accommodation_actual + food_actual + cost_breakdown["transport"] + cost_breakdown["attractions"] + cost_breakdown["buffer"]
    )

    return {
        "accommodation_actual": round(accommodation_actual),
        "food_actual": round(food_actual),
        "total_actual": round(total_actual),
    }


def validate_costs(state: PlannerState) -> PlannerState:
    low, high = state["cost_breakdown"]["target_range_inr"]
    actual = estimate_actual_cost(state)

    if actual["total_actual"] > high:
        # ponytail: one corrective retry with the overage as feedback, then accept best-effort
        feedback = (
            f"Your previous suggestions came out around Rs.{actual['total_actual']} total, "
            f"which is over this traveler's Rs.{high} budget ceiling. Suggest cheaper options."
        )
        hotels = _select_hotels(state, feedback)
        restaurants = _select_restaurants(state, feedback)
        state = {**state, "hotels": hotels, "restaurants": restaurants}
        actual = estimate_actual_cost(state)

    cost_breakdown = {**state["cost_breakdown"], **actual}

    if actual["total_actual"] > high:
        return {
            **state,
            "cost_breakdown": cost_breakdown,
            "budget_status": "too_high",
            "budget_message": (
                f"The hotels and restaurants available for {state.get('destination')} come to roughly "
                f"Rs.{actual['total_actual']} for this trip, above your Rs.{state['budget']} budget. "
                "Lower the budget or upgrade the experience for better-matched options."
            ),
        }

    return {**state, "cost_breakdown": cost_breakdown}


def cost_validation_router(state: PlannerState) -> str:
    return state["budget_status"]


def select_attractions(state: PlannerState) -> PlannerState:
    attractions = ["Tea Gardens", "Waterfalls", "View Point"]
    return {**state, "attractions": attractions}


def add_extras(state: PlannerState) -> PlannerState:
    destination = state["destination"]
    optional_inclusions = [
        {
            "name": "Guided heritage walk",
            "description": f"A local guide-led walking tour around {destination}.",
            "price_inr": 800,
        },
        {
            "name": "Adventure activity add-on",
            "description": "One paid adventure activity (e.g. trekking, water sports) per adult.",
            "price_inr": 1200,
        },
    ]

    preferences = ", ".join(state.get("preferences", [])) or "your trip goals"
    why_this_fits = (
        f"{destination} was matched to your {state['days']}-day trip for {preferences}, "
        f"and the plan keeps spending within Rs.{state['cost_breakdown']['target_range_inr'][0]}"
        f"-Rs.{state['cost_breakdown']['target_range_inr'][1]}."
    )

    return {**state, "optional_inclusions": optional_inclusions, "why_this_fits": why_this_fits}


def fetch_weather(state: PlannerState) -> PlannerState:
    start_date = state.get("start_date")
    if not start_date:
        return {**state, "weather": []}

    try:
        parsed = date.fromisoformat(start_date)
    except ValueError:
        return {**state, "weather": []}

    forecast = fetch_forecast(state["destination"], parsed, state["days"])
    return {**state, "weather": forecast or []}


def _format_weather(weather: List[dict]) -> str:
    if not weather:
        return "No forecast available."
    return "\n".join(
        f"{day['date']}: {day['summary']}, {day['temp_min']}-{day['temp_max']}C"
        + (" (rain likely)" if day["rain_likely"] else "")
        for day in weather
    )


def assemble_itinerary(state: PlannerState) -> PlannerState:
    llm = get_llm()

    response = llm.invoke(
        itinerary_prompt.format_messages(
            budget=state["budget"],
            adults=state["adults"],
            children=state["children"],
            days=state["days"],
            starting_city=state.get("starting_city") or "Not specified",
            destination=state["destination"],
            preferences=", ".join(state["preferences"]),
            hotel_type=state["hotel_type"],
            food_preferences=", ".join(state["food_preferences"]),
            must_visit_places=", ".join(state.get("must_visit_places", [])) or "None specified",
            mobility_constraints=state.get("mobility_constraints") or "None",
            cost_breakdown=state["cost_breakdown"],
            restaurant_names=", ".join(r["name"] for r in state["restaurants"]),
            weather_forecast=_format_weather(state.get("weather", [])),
            language=state.get("language") or "English",
        )
    )

    raw = re.sub(r"```json|```", "", response.content.strip()).strip()
    try:
        itinerary = json.loads(raw)
    except json.JSONDecodeError:
        itinerary = [
            {
                "day": day,
                "morning": raw if day == 1 else "",
                "afternoon": "",
                "evening": "",
                "meals": {"breakfast": "", "lunch": "", "dinner": ""},
            }
            for day in range(1, state["days"] + 1)
        ]

    return {**state, "itinerary": itinerary}


def invalid_input(state: PlannerState) -> PlannerState:
    return state


def build_workflow():
    workflow = StateGraph(PlannerState)

    workflow.add_node("validate_inputs", validate_inputs)
    workflow.add_node("suggest_destinations", suggest_destinations)
    workflow.add_node("budget_feasibility", budget_feasibility)
    workflow.add_node("budget_allocator", budget_allocator)
    workflow.add_node("select_hotels", select_hotels)
    workflow.add_node("select_restaurants", select_restaurants)
    workflow.add_node("validate_costs", validate_costs)
    workflow.add_node("select_attractions", select_attractions)
    workflow.add_node("add_extras", add_extras)
    workflow.add_node("fetch_weather", fetch_weather)
    workflow.add_node("assemble_itinerary", assemble_itinerary)
    workflow.add_node("invalid_input", invalid_input)

    workflow.set_entry_point("validate_inputs")

    workflow.add_conditional_edges(
        "validate_inputs",
        destination_router,
        {
            "invalid": "invalid_input",
            "suggest": "suggest_destinations",
            "continue": "budget_feasibility",
        },
    )

    workflow.add_edge("suggest_destinations", "budget_feasibility")
    workflow.add_conditional_edges(
        "budget_feasibility",
        feasibility_router,
        {
            "too_low": END,
            "too_high": END,
            "feasible": "budget_allocator",
        },
    )
    workflow.add_edge("budget_allocator", "select_hotels")
    workflow.add_edge("select_hotels", "select_restaurants")
    workflow.add_edge("select_restaurants", "validate_costs")
    workflow.add_conditional_edges(
        "validate_costs",
        cost_validation_router,
        {
            "too_high": END,
            "feasible": "select_attractions",
        },
    )
    workflow.add_edge("select_attractions", "add_extras")
    workflow.add_edge("add_extras", "fetch_weather")
    workflow.add_edge("fetch_weather", "assemble_itinerary")
    workflow.add_edge("assemble_itinerary", END)
    workflow.add_edge("invalid_input", END)

    return workflow.compile()


planner_app = build_workflow()
