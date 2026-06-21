# TripPilot API

FastAPI backend wrapping the LangGraph travel-planning workflow (budget allocation, hotel recommendations via Groq LLM, itinerary generation).

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set your real `GROQ_API_KEY`.

## Run

```
uvicorn app.main:app --reload
```

API docs: http://127.0.0.1:8000/docs

## Endpoints

- `GET /health`
- `POST /plan-trip` — body:

```json
{
  "budget": 80000,
  "adults": 2,
  "children": 1,
  "days": 5,
  "preferences": ["Nature", "Adventure"],
  "destination": "Munnar",
  "hotel_type": "Standard",
  "food_preferences": ["Vegetarian"]
}
```

`destination` is optional — if omitted, the API auto-suggests one based on your preferences and proceeds.
