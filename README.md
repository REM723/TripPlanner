# TripPilot

An AI-powered tour planner for Indian middle-class travelers. Given a budget, traveler
count, trip length, and sightseeing preferences, it suggests a destination (if none is
given), validates whether the budget is feasible, and generates hotels, restaurants, a
day-by-day itinerary, and a budget breakdown.

Two extra touches: a **start date** triggers a real weather forecast (via Open-Meteo)
that the itinerary is planned around — rainy days get indoor activities instead of
outdoor ones — and a **language** picker generates the hotel highlights, restaurant
details, and itinerary text directly in the chosen Indian language.

The budget check is the core feature: a submitted plan can come back **feasible**,
**too low** (asks for a revised budget), or **too high** (offers to lower the budget or
upgrade the experience). The UI loops through this until the user lands on a feasible
plan or gives up.

## Architecture

- **`backend/`** — FastAPI + LangGraph. A single `POST /plan-trip` endpoint runs a graph
  that validates input, optionally suggests a destination, checks budget feasibility,
  then (if feasible) fetches a weather forecast (`app/weather.py`, stdlib `urllib`
  against Open-Meteo — no API key) and generates hotels, restaurants, and a day-by-day
  itinerary via a Groq LLM, all in the requested language.
- **`frontend/`** — React + TypeScript + Vite + Tailwind. A state machine
  (`src/state/plannerMachine.ts`) drives the flow: input → destination suggestion →
  budget revision (looping) → results. All backend wire-format details are isolated in
  `src/api/planApi.ts`.

## Setup

### Backend

```
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` and set a real `GROQ_API_KEY` (get one at console.groq.com). Never commit
`.env` or paste the key anywhere outside that file.

```
uvicorn app.main:app --port 8000
```

API docs: http://127.0.0.1:8000/docs

> Note: `--reload` has been unreliable in some Windows setups (WatchFiles silently
> missing edits). If a code change doesn't seem to take effect, stop the process and
> restart it manually instead of relying on auto-reload.

### Frontend

```
cd frontend
npm install
npm run dev
```

Runs at http://localhost:5173 (or the next free port) and proxies `/api/*` to the
backend at `http://127.0.0.1:8000` (see `vite.config.ts`).

## API contract

`POST /plan-trip`

```json
{
  "budget": 80000,
  "adults": 2,
  "children": 1,
  "days": 5,
  "preferences": ["Nature", "Adventure"],
  "destination": "Munnar",
  "hotel_type": "Standard",
  "food_preferences": ["Vegetarian"],
  "starting_city": "Bangalore",
  "must_visit_places": ["Tea Museum"],
  "mobility_constraints": "None",
  "start_date": "2026-07-01",
  "language": "Hindi"
}
```

`destination` is optional — if omitted, the backend picks one from a fixed list based on
preferences and returns `suggested_destinations` alongside it.

`start_date` is optional (ISO `YYYY-MM-DD`). If it falls within the next 15 days (Open-
Meteo's free forecast horizon) and not in the past, the response includes a `weather`
array and the itinerary is planned around it; otherwise `weather` is empty and planning
falls back to no weather input.

`language` defaults to `"English"`. AI-generated text (hotel highlights, restaurant
details, the itinerary) is written in this language; field names, prices, and other
structural data stay as-is.

Response `status` is one of:

- `"ok"` — feasible plan with `hotels`, `restaurants`, `itinerary`, `weather`,
  `cost_breakdown`, `optional_inclusions`, and `why_this_fits`.
- `"budget_too_low"` — `message` and `minimum_viable_budget`.
- `"budget_too_high"` — `message` and `suggested_actions`
  (`lower_budget` / `upgrade_experience`).

Feasibility is based on per-day-per-person spend (₹1,200–₹6,000/day/person), except a
`Luxury` hotel type lifts the upper bound.

## Tech stack

- Backend: FastAPI, LangGraph, LangChain, Groq (`llama-3.3-70b-versatile`), Open-Meteo
  (weather, free/no key)
- Frontend: React 19, TypeScript, Vite, Tailwind CSS v4
