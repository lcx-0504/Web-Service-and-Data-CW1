# NutriTrack — Food Nutrition Tracking & Analysis API

A data-driven REST API for food nutrition tracking and dietary analysis, powered by the USDA SR Legacy dataset (7,793 foods). Includes a Model Context Protocol (MCP) server that enables AI assistants (e.g. Claude Desktop) to interact with the API through natural language.

> **Course**: XJCO3011 Web Services and Web Data — Coursework 1

## Features

- **Food Database** — 7,793 foods from USDA SR Legacy with full nutritional data (calories, protein, fat, carbs, fiber per 100g)
- **Meal Tracking** — Log meals with food items and quantities, full CRUD operations
- **Nutrition Analytics** — Daily summaries, weekly trends, and balance analysis against recommended daily intake
- **Personalized Recommendations** — BMR-based daily targets using the Mifflin-St Jeor equation (adjusts for age, gender, height, weight, activity level)
- **Input Validation** — Two-tier validation: hard rejection for impossible values + soft warnings for extreme-but-possible values
- **JWT Authentication** — Secure token-based auth for all user-specific endpoints
- **MCP Integration** — 15 MCP tools wrapping all API endpoints, usable from Claude Desktop, ChatBox, or any MCP-compatible client

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | SQLite (via aiosqlite) |
| ORM | SQLAlchemy 2.0 (async) |
| Migration | Alembic |
| Auth | JWT (python-jose) |
| MCP | [mcp](https://pypi.org/project/mcp/) (official Python SDK, FastMCP) |
| Data | USDA FoodData Central — SR Legacy (April 2018) |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Environment config
│   │   ├── database.py          # SQLAlchemy async engine
│   │   ├── auth/
│   │   │   └── jwt.py           # JWT creation/verification
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── user.py          # User (with profile fields)
│   │   │   ├── food.py          # Food (USDA nutritional data)
│   │   │   ├── meal.py          # Meal (daily meal records)
│   │   │   └── meal_item.py     # MealItem (food + quantity)
│   │   ├── routers/             # API route handlers
│   │   │   ├── auth.py          # Register, login
│   │   │   ├── foods.py         # Food list, search, detail
│   │   │   ├── meals.py         # Meal CRUD
│   │   │   ├── analytics.py     # Daily/weekly/balance analysis
│   │   │   └── users.py         # User profile get/update
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── data/
│   │       └── import_usda.py   # USDA CSV import script
│   ├── alembic/                 # Database migrations
│   ├── pyproject.toml
│   └── .env                     # Environment variables
├── mcp_server/
│   ├── server.py                # MCP Server (15 tools, stdio mode)
│   └── config.py                # API base URL config
├── dataset/
│   └── sr_legacy/               # USDA SR Legacy CSV files
└── docs/
    ├── api-documentation.md
    ├── technical-report.md
    └── genai-logs/
```

## Quick Start

### Prerequisites

- Python 3.11+ (recommended: 3.12 via conda)
- conda (for environment management)

### 1. Clone & Setup Environment

```bash
git clone <repository-url>
cd Web-Service-and-Data-CW1

# Create conda environment
conda create -n nutritrack python=3.12 -y
conda activate nutritrack

# Install dependencies
cd backend
pip install -e .
pip install python-multipart email-validator bcrypt==4.0.1
```

### 2. Configure Environment Variables

```bash
# backend/.env (already included with defaults)
DATABASE_URL=sqlite+aiosqlite:///./nutritrack.db
SECRET_KEY=dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3. Initialize Database & Import Data

```bash
# Run Alembic migrations
cd backend
alembic upgrade head

# Import USDA food data (requires dataset/sr_legacy/ CSV files)
python -m app.data.import_usda
```

This imports 7,793 foods from the USDA SR Legacy dataset into the SQLite database.

### 4. Start the API Server

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

The API is now available at:
- **API root**: http://127.0.0.1:8000
- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## API Endpoints

### Authentication (public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register a new user |
| POST | `/api/auth/login` | Login and receive JWT token |

### Foods (public)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/foods/` | List foods (paginated, filterable by category) |
| GET | `/api/foods/search?q=` | Search foods by name |
| GET | `/api/foods/{id}` | Get food nutritional details |

### Meals (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/meals/` | List user's meal records |
| POST | `/api/meals/` | Log a new meal with food items |
| GET | `/api/meals/{id}` | Get meal details |
| PUT | `/api/meals/{id}` | Update a meal |
| DELETE | `/api/meals/{id}` | Delete a meal |

### Analytics (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analytics/daily?date=` | Daily nutritional summary |
| GET | `/api/analytics/weekly?start=` | 7-day nutritional trend |
| GET | `/api/analytics/balance?date=` | Balance analysis vs. recommended intake |

### User Profile (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/users/profile` | Get user profile |
| PUT | `/api/users/profile` | Update profile (height, weight, age, etc.) |

### Usage Example

```bash
# Register
curl -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "email": "test@example.com", "password": "test1234"}'

# Login (get token)
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -d "username=testuser&password=test1234" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Search foods
curl "http://127.0.0.1:8000/api/foods/search?q=chicken+breast"

# Log a meal
curl -X POST http://127.0.0.1:8000/api/meals/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"meal_type": "lunch", "date": "2026-04-09", "items": [{"food_id": 1, "quantity": 200}]}'

# Get daily summary
curl -H "Authorization: Bearer $TOKEN" \
  "http://127.0.0.1:8000/api/analytics/daily?date=2026-04-09"
```

## MCP Server Setup

The MCP server wraps all 15 API endpoints as tools, enabling AI assistants to interact with NutriTrack through natural language conversation.

### Claude Desktop Configuration

1. **Ensure the API server is running** (see Quick Start step 4)

2. **Edit Claude Desktop config** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "NutriTrack": {
      "command": "/opt/anaconda3/envs/nutritrack/bin/python",
      "args": ["/absolute/path/to/Web-Service-and-Data-CW1/mcp_server/server.py"]
    }
  }
}
```

> Replace `/absolute/path/to/` with the actual path on your machine, and adjust the Python path if your conda is installed elsewhere.

3. **Restart Claude Desktop**

4. **Test it** — In a new Claude conversation, try:
   - "Search for foods containing 'apple'"
   - "Login with testuser / test1234, then show my daily nutrition summary for today"
   - "Log a breakfast: 2 eggs (100g each) and a banana (120g)"

### ChatBox Configuration

Use the same stdio configuration:
- **Command**: `/opt/anaconda3/envs/nutritrack/bin/python`
- **Args**: `["/absolute/path/to/Web-Service-and-Data-CW1/mcp_server/server.py"]`

### Available MCP Tools (15)

| Tool | Auth Required | Description |
|------|:---:|-------------|
| `register` | No | Register a new account |
| `login` | No | Login and store JWT token |
| `search_food` | No | Search foods by name |
| `list_foods` | No | List foods with pagination/filtering |
| `get_food_detail` | No | Get detailed nutrition for a food |
| `log_meal` | Yes | Record a meal with food items |
| `list_meals` | Yes | View meal history |
| `get_meal` | Yes | View a specific meal |
| `update_meal` | Yes | Modify a meal record |
| `delete_meal` | Yes | Remove a meal record |
| `get_daily_summary` | Yes | Daily calorie & macro totals |
| `get_weekly_trend` | Yes | 7-day nutrition trend |
| `analyze_balance` | Yes | Compare intake vs. recommended values |
| `get_profile` | Yes | View user profile |
| `update_profile` | Yes | Update height, weight, age, etc. |

## Data Source

- **USDA FoodData Central — SR Legacy** (April 2018)
- 7,793 common foods with nutritional data per 100g
- 28 food categories (Dairy, Poultry, Fruits, Vegetables, etc.)
- Source: https://fdc.nal.usda.gov/download-datasets

## Documentation

- [API Documentation](docs/api-documentation.md) (also available as PDF)
- [Technical Report](docs/technical-report.md)

## License

This project is for academic purposes (XJCO3011 Coursework 1).