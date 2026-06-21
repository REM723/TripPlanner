from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .graph import planner_app
from .models import TripRequest, TripResponse

app = FastAPI(title="TripPilot API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/plan-trip", response_model=TripResponse)
def plan_trip(request: TripRequest) -> TripResponse:
    state = {
        "budget": request.budget,
        "adults": request.adults,
        "children": request.children,
        "days": request.days,
        "preferences": request.preferences,
        "destination": request.destination,
        "hotel_type": request.hotel_type,
        "food_preferences": request.food_preferences,
        "starting_city": request.starting_city,
        "must_visit_places": request.must_visit_places,
        "mobility_constraints": request.mobility_constraints,
        "start_date": request.start_date,
        "language": request.language,
        "weather": [],
        "input_valid": False,
        "validation_errors": [],
        "destination_was_suggested": False,
        "suggested_destinations": [],
        "cost_breakdown": {},
        "budget_status": "",
        "budget_message": "",
        "minimum_viable_budget": None,
        "hotels": [],
        "restaurants": [],
        "attractions": [],
        "optional_inclusions": [],
        "why_this_fits": "",
        "itinerary": [],
    }

    result = planner_app.invoke(state)

    if not result["input_valid"]:
        raise HTTPException(status_code=400, detail=result["validation_errors"])

    if result["budget_status"] == "too_low":
        return TripResponse(
            status="budget_too_low",
            message=result["budget_message"],
            minimum_viable_budget=result["minimum_viable_budget"],
            destination=result["destination"],
            destination_was_suggested=result["destination_was_suggested"],
            suggested_destinations=result["suggested_destinations"],
        )

    if result["budget_status"] == "too_high":
        return TripResponse(
            status="budget_too_high",
            message=result["budget_message"],
            suggested_actions=["lower_budget", "upgrade_experience"],
            destination=result["destination"],
            destination_was_suggested=result["destination_was_suggested"],
            suggested_destinations=result["suggested_destinations"],
        )

    return TripResponse(
        status="ok",
        destination=result["destination"],
        destination_was_suggested=result["destination_was_suggested"],
        suggested_destinations=result["suggested_destinations"],
        cost_breakdown=result["cost_breakdown"],
        hotels=result["hotels"],
        restaurants=result["restaurants"],
        attractions=result["attractions"],
        optional_inclusions=result["optional_inclusions"],
        itinerary=result["itinerary"],
        weather=result["weather"],
        why_this_fits=result["why_this_fits"],
    )
