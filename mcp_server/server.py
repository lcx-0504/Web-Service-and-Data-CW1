"""
NutriTrack MCP Server

Wraps the NutriTrack REST API as MCP tools for AI assistants.

Usage (stdio mode):
    cd mcp_server/
    conda activate nutritrack
    python server.py
"""

import json
import os
import sys

# Ensure the mcp_server directory is on the path so `config` can be found
# regardless of the working directory when launched by MCP clients.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
import httpx

from config import API_BASE_URL

mcp = FastMCP(
    "NutriTrack",
    instructions="Food nutrition tracking and analysis tools. Search foods, log meals, and analyze nutrition.",
)

# Store JWT token for authenticated requests
_auth_token: str | None = None


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if _auth_token:
        headers["Authorization"] = f"Bearer {_auth_token}"
    return headers


async def _api_get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        resp = await client.get(path, params=params, headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def _api_post(path: str, data: dict) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        resp = await client.post(path, json=data, headers=_headers())
        resp.raise_for_status()
        return resp.json()


# ─────────────────── Auth Tool ───────────────────


@mcp.tool()
async def login(username: str, password: str) -> str:
    """Log in to NutriTrack and store the authentication token.
    Must be called before using tools that require authentication (log_meal, get_daily_summary, etc.).
    """
    global _auth_token
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        resp = await client.post(
            "/api/auth/login",
            data={"username": username, "password": password},
        )
        if resp.status_code != 200:
            return f"Login failed: {resp.text}"
        _auth_token = resp.json()["access_token"]
        return f"Logged in as {username} successfully."


@mcp.tool()
async def register(username: str, email: str, password: str) -> str:
    """Register a new NutriTrack user account."""
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        resp = await client.post(
            "/api/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        if resp.status_code != 201:
            return f"Registration failed: {resp.text}"
        return f"User {username} registered successfully. Use the login tool to authenticate."


# ─────────────────── Food Tools ───────────────────


@mcp.tool()
async def search_food(query: str, page: int = 1, per_page: int = 10) -> str:
    """Search for foods in the NutriTrack database by name.
    Returns a list of matching foods with their nutritional information (per 100g).
    """
    result = await _api_get("/api/foods/search", params={"q": query, "page": page, "per_page": per_page})
    foods = result["items"]
    if not foods:
        return f"No foods found matching '{query}'."

    lines = [f"Found {result['total']} results (showing page {result['page']}):\n"]
    for f in foods:
        lines.append(
            f"- **{f['name']}** (ID: {f['id']})\n"
            f"  Category: {f['category']}\n"
            f"  Per 100g: {f['calories']} kcal | Protein: {f['protein']}g | "
            f"Fat: {f['fat']}g | Carbs: {f['carbs']}g | Fiber: {f['fiber']}g"
        )
    return "\n".join(lines)


@mcp.tool()
async def get_food_detail(food_id: int) -> str:
    """Get detailed nutritional information for a specific food item by its ID."""
    try:
        f = await _api_get(f"/api/foods/{food_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Food with ID {food_id} not found."
        raise

    return (
        f"**{f['name']}**\n"
        f"- USDA FDC ID: {f['fdc_id']}\n"
        f"- Category: {f['category']}\n"
        f"- Nutritional values per 100g:\n"
        f"  - Calories: {f['calories']} kcal\n"
        f"  - Protein: {f['protein']} g\n"
        f"  - Fat: {f['fat']} g\n"
        f"  - Carbohydrates: {f['carbs']} g\n"
        f"  - Fiber: {f['fiber']} g"
    )


# ─────────────────── Meal Tool ───────────────────


@mcp.tool()
async def log_meal(
    date: str,
    meal_type: str,
    items: list[dict],
    notes: str | None = None,
) -> str:
    """Log a meal with food items. Requires authentication (call login first).

    Args:
        date: Date in YYYY-MM-DD format
        meal_type: One of 'breakfast', 'lunch', 'dinner', 'snack'
        items: List of food items, each with 'food_id' (int) and 'quantity' (float, in grams)
        notes: Optional notes about the meal
    """
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    payload = {
        "date": date,
        "meal_type": meal_type,
        "items": items,
    }
    if notes:
        payload["notes"] = notes

    try:
        result = await _api_post("/api/meals/", payload)
    except httpx.HTTPStatusError as e:
        return f"Failed to log meal: {e.response.text}"

    total_cal = sum(
        item["food"]["calories"] * item["quantity"] / 100
        for item in result["items"]
    )
    item_desc = ", ".join(
        f"{item['food']['name']} ({item['quantity']}g)" for item in result["items"]
    )
    return (
        f"Meal logged successfully! (ID: {result['id']})\n"
        f"- Date: {result['date']}, Type: {result['meal_type']}\n"
        f"- Items: {item_desc}\n"
        f"- Estimated calories: {total_cal:.0f} kcal"
    )


# ─────────────────── Analytics Tools ───────────────────


@mcp.tool()
async def get_daily_summary(date: str) -> str:
    """Get a nutrition summary for a specific date. Requires authentication.

    Args:
        date: Date in YYYY-MM-DD format
    """
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    try:
        result = await _api_get("/api/analytics/daily", params={"date": date})
    except httpx.HTTPStatusError as e:
        return f"Failed to get daily summary: {e.response.text}"

    t = result["total"]
    return (
        f"Nutrition summary for {result['date']}:\n"
        f"- Meals eaten: {result['meal_count']}\n"
        f"- Total Calories: {t['calories']} kcal\n"
        f"- Protein: {t['protein']} g\n"
        f"- Fat: {t['fat']} g\n"
        f"- Carbohydrates: {t['carbs']} g\n"
        f"- Fiber: {t['fiber']} g"
    )


@mcp.tool()
async def get_weekly_trend(start_date: str) -> str:
    """Get a 7-day nutrition trend starting from the given date. Requires authentication.

    Args:
        start_date: Start date in YYYY-MM-DD format
    """
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    try:
        result = await _api_get("/api/analytics/weekly", params={"start": start_date})
    except httpx.HTTPStatusError as e:
        return f"Failed to get weekly trend: {e.response.text}"

    lines = [f"Weekly nutrition trend ({result['start_date']} to {result['end_date']}):\n"]
    for day in result["daily"]:
        t = day["total"]
        if day["meal_count"] > 0:
            lines.append(
                f"  {day['date']}: {t['calories']} kcal | "
                f"P: {t['protein']}g | F: {t['fat']}g | C: {t['carbs']}g "
                f"({day['meal_count']} meals)"
            )
        else:
            lines.append(f"  {day['date']}: No meals recorded")

    avg = result["average"]
    lines.append(
        f"\nDaily average: {avg['calories']} kcal | "
        f"P: {avg['protein']}g | F: {avg['fat']}g | C: {avg['carbs']}g"
    )
    return "\n".join(lines)


@mcp.tool()
async def analyze_balance(date: str) -> str:
    """Analyze nutritional balance for a specific date compared to FDA recommended daily values.
    Requires authentication.

    Args:
        date: Date in YYYY-MM-DD format
    """
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    try:
        result = await _api_get("/api/analytics/balance", params={"date": date})
    except httpx.HTTPStatusError as e:
        return f"Failed to analyze balance: {e.response.text}"

    lines = [f"Nutritional balance for {result['date']}:\n"]
    status_emoji = {"low": "⚠️ Low", "ok": "✅ OK", "high": "⚡ High"}
    for item in result["items"]:
        emoji = status_emoji.get(item["status"], item["status"])
        lines.append(
            f"  {item['nutrient'].capitalize()}: {item['actual']} / {item['recommended']} "
            f"({item['percentage']}%) — {emoji}"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run(transport="stdio")
