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


async def _api_put(path: str, data: dict) -> dict:
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        resp = await client.put(path, json=data, headers=_headers())
        resp.raise_for_status()
        return resp.json()


async def _api_delete(path: str) -> int:
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        resp = await client.delete(path, headers=_headers())
        resp.raise_for_status()
        return resp.status_code


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
async def list_categories() -> str:
    """List all available food categories in the database."""
    categories = await _api_get("/api/foods/categories")
    lines = [f"Available food categories ({len(categories)}):\n"]
    for c in categories:
        lines.append(f"- {c}")
    return "\n".join(lines)


@mcp.tool()
async def search_food(query: str, category: str | None = None, page: int = 1, per_page: int = 10) -> str:
    """Search for foods in the NutriTrack database by name.
    Optionally filter by category (use list_categories to see available categories).
    Returns a list of matching foods with their nutritional information (per 100g).
    """
    params = {"q": query, "page": page, "per_page": per_page}
    if category:
        params["category"] = category
    result = await _api_get("/api/foods/search", params=params)
    foods = result["items"]
    if not foods:
        msg = f"No foods found matching '{query}'"
        if category:
            msg += f" in category '{category}'"
        return msg + "."

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


# ─────────────────── Profile Tools ───────────────────


@mcp.tool()
async def get_profile() -> str:
    """Get the current user's profile including personal info. Requires authentication."""
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    try:
        result = await _api_get("/api/users/profile")
    except httpx.HTTPStatusError as e:
        return f"Failed to get profile: {e.response.text}"

    lines = [f"Profile for **{result['username']}**:"]
    lines.append(f"- Email: {result['email']}")
    if result.get("height"):
        lines.append(f"- Height: {result['height']} cm")
    if result.get("weight"):
        lines.append(f"- Weight: {result['weight']} kg")
    if result.get("age"):
        lines.append(f"- Age: {result['age']}")
    if result.get("gender"):
        lines.append(f"- Gender: {result['gender']}")
    if result.get("activity_level"):
        lines.append(f"- Activity level: {result['activity_level']}")
    if not any(result.get(k) for k in ["height", "weight", "age", "gender"]):
        lines.append("- No personal info set. Use update_profile to add your height, weight, age, etc.")
    warnings = result.get("warnings", [])
    if warnings:
        lines.append("\n⚠️ Warnings:")
        for w in warnings:
            lines.append(f"  - {w}")
    return "\n".join(lines)


@mcp.tool()
async def update_profile(
    height: float | None = None,
    weight: float | None = None,
    age: int | None = None,
    gender: str | None = None,
    activity_level: str | None = None,
) -> str:
    """Update the current user's profile for personalized nutrition recommendations.
    Requires authentication.

    Args:
        height: Height in cm
        weight: Weight in kg
        age: Age in years
        gender: 'male' or 'female'
        activity_level: One of 'sedentary', 'light', 'moderate', 'active', 'very_active'
    """
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    payload = {}
    if height is not None:
        payload["height"] = height
    if weight is not None:
        payload["weight"] = weight
    if age is not None:
        payload["age"] = age
    if gender is not None:
        payload["gender"] = gender
    if activity_level is not None:
        payload["activity_level"] = activity_level

    if not payload:
        return "No fields to update. Please provide at least one field."

    try:
        result = await _api_put("/api/users/profile", payload)
    except httpx.HTTPStatusError as e:
        return f"Failed to update profile: {e.response.text}"

    lines = [
        f"Profile updated successfully!",
        f"- Height: {result.get('height', 'N/A')} cm",
        f"- Weight: {result.get('weight', 'N/A')} kg",
        f"- Age: {result.get('age', 'N/A')}",
        f"- Gender: {result.get('gender', 'N/A')}",
        f"- Activity level: {result.get('activity_level', 'N/A')}",
    ]
    warnings = result.get("warnings", [])
    if warnings:
        lines.append("\n⚠️ Warnings:")
        for w in warnings:
            lines.append(f"  - {w}")
    return "\n".join(lines)


# ─────────────────── Food List Tool ───────────────────


@mcp.tool()
async def list_foods(page: int = 1, per_page: int = 10, category: str | None = None) -> str:
    """List foods from the database with optional category filter and pagination.

    Args:
        page: Page number (default 1)
        per_page: Items per page (default 10)
        category: Optional category to filter by (e.g. 'Dairy and Egg Products', 'Fruits and Fruit Juices')
    """
    params: dict = {"page": page, "per_page": per_page}
    if category:
        params["category"] = category

    result = await _api_get("/api/foods/", params=params)
    foods = result["items"]
    if not foods:
        return "No foods found."

    lines = [f"Foods (page {result['page']}/{(result['total'] + result['per_page'] - 1) // result['per_page']}, total: {result['total']}):\n"]
    for f in foods:
        lines.append(
            f"- **{f['name']}** (ID: {f['id']}, {f['category']})\n"
            f"  {f['calories']} kcal | P: {f['protein']}g | F: {f['fat']}g | C: {f['carbs']}g"
        )
    return "\n".join(lines)


# ─────────────────── Meal Management Tools ───────────────────


@mcp.tool()
async def list_meals(page: int = 1, per_page: int = 10) -> str:
    """List the current user's meal records with pagination. Requires authentication.

    Args:
        page: Page number (default 1)
        per_page: Items per page (default 10)
    """
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    try:
        result = await _api_get("/api/meals/", params={"page": page, "per_page": per_page})
    except httpx.HTTPStatusError as e:
        return f"Failed to list meals: {e.response.text}"

    meals = result["items"]
    if not meals:
        return "No meals recorded yet."

    lines = [f"Meals (total: {result['total']}):\n"]
    for m in meals:
        item_count = len(m.get("items", []))
        lines.append(
            f"- **Meal #{m['id']}** — {m['date']} {m['meal_type']}"
            f" ({item_count} items)"
        )
        if m.get("notes"):
            lines.append(f"  Notes: {m['notes']}")
    return "\n".join(lines)


@mcp.tool()
async def get_meal(meal_id: int) -> str:
    """Get detailed information about a specific meal, including all food items and quantities.
    Requires authentication.

    Args:
        meal_id: The ID of the meal to retrieve
    """
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    try:
        m = await _api_get(f"/api/meals/{meal_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Meal with ID {meal_id} not found."
        return f"Failed to get meal: {e.response.text}"

    lines = [
        f"**Meal #{m['id']}** — {m['date']} {m['meal_type']}",
    ]
    if m.get("notes"):
        lines.append(f"Notes: {m['notes']}")
    lines.append("Items:")

    total_cal = 0
    for item in m.get("items", []):
        food = item["food"]
        cal = food["calories"] * item["quantity"] / 100
        total_cal += cal
        lines.append(
            f"  - {food['name']}: {item['quantity']}g "
            f"({cal:.0f} kcal, P: {food['protein'] * item['quantity'] / 100:.1f}g)"
        )
    lines.append(f"Total: ~{total_cal:.0f} kcal")
    return "\n".join(lines)


@mcp.tool()
async def update_meal(
    meal_id: int,
    date: str | None = None,
    meal_type: str | None = None,
    items: list[dict] | None = None,
    notes: str | None = None,
) -> str:
    """Update an existing meal record. Requires authentication.

    Args:
        meal_id: The ID of the meal to update
        date: New date in YYYY-MM-DD format (optional)
        meal_type: New meal type (optional)
        items: New list of food items, each with 'food_id' and 'quantity' (optional, replaces all items)
        notes: New notes (optional)
    """
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    payload = {}
    if date is not None:
        payload["date"] = date
    if meal_type is not None:
        payload["meal_type"] = meal_type
    if items is not None:
        payload["items"] = items
    if notes is not None:
        payload["notes"] = notes

    if not payload:
        return "No fields to update. Provide at least one of: date, meal_type, items, notes."

    try:
        result = await _api_put(f"/api/meals/{meal_id}", payload)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Meal with ID {meal_id} not found."
        return f"Failed to update meal: {e.response.text}"

    return f"Meal #{result['id']} updated successfully ({result['date']} {result['meal_type']})."


@mcp.tool()
async def delete_meal(meal_id: int) -> str:
    """Delete a meal record. Requires authentication.

    Args:
        meal_id: The ID of the meal to delete
    """
    if not _auth_token:
        return "Error: Not authenticated. Please call the login tool first."

    try:
        await _api_delete(f"/api/meals/{meal_id}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return f"Meal with ID {meal_id} not found."
        return f"Failed to delete meal: {e.response.text}"

    return f"Meal #{meal_id} deleted successfully."


if __name__ == "__main__":
    mcp.run(transport="stdio")
