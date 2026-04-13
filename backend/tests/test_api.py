"""
NutriTrack API Integration Tests

Usage:
    # Test local server (default)
    pytest tests/test_api.py -v

    # Test remote PythonAnywhere
    pytest tests/test_api.py -v --base-url https://lichenxi.pythonanywhere.com

    # Test with a custom base URL
    pytest tests/test_api.py -v --base-url http://127.0.0.1:9000
"""

import datetime as dt
import uuid

import pytest
import requests


# ---------------------------------------------------------------------------
# Fixtures & Config
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def base_url(request):
    return request.config.getoption("--base-url").rstrip("/")


@pytest.fixture(scope="session")
def unique_user():
    """Generate a unique test user to avoid conflicts."""
    uid = uuid.uuid4().hex[:8]
    return {
        "username": f"test_{uid}",
        "email": f"test_{uid}@example.com",
        "password": "testpass123",
    }


@pytest.fixture(scope="session")
def auth_token(base_url, unique_user):
    """Register + login, return Bearer token."""
    # Register
    r = requests.post(f"{base_url}/api/auth/register", json=unique_user)
    assert r.status_code == 201, f"Register failed: {r.text}"

    # Login (OAuth2 form)
    r = requests.post(
        f"{base_url}/api/auth/login",
        data={"username": unique_user["username"], "password": unique_user["password"]},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    return token


@pytest.fixture(scope="session")
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class TestRoot:
    def test_root(self, base_url):
        r = requests.get(f"{base_url}/")
        assert r.status_code == 200
        assert "NutriTrack" in r.json()["message"]


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class TestAuth:
    def test_register_success(self, base_url):
        uid = uuid.uuid4().hex[:8]
        r = requests.post(f"{base_url}/api/auth/register", json={
            "username": f"reg_{uid}",
            "email": f"reg_{uid}@example.com",
            "password": "pass1234",
        })
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["username"] == f"reg_{uid}"

    def test_register_duplicate(self, base_url, unique_user, auth_token):
        """Re-registering the same user should fail."""
        r = requests.post(f"{base_url}/api/auth/register", json=unique_user)
        assert r.status_code == 400

    def test_register_invalid_username(self, base_url):
        r = requests.post(f"{base_url}/api/auth/register", json={
            "username": "ab",  # too short
            "email": "short@example.com",
            "password": "pass1234",
        })
        assert r.status_code == 422

    def test_login_success(self, base_url, unique_user, auth_token):
        r = requests.post(f"{base_url}/api/auth/login", data={
            "username": unique_user["username"],
            "password": unique_user["password"],
        })
        assert r.status_code == 200
        assert "access_token" in r.json()

    def test_login_wrong_password(self, base_url, unique_user):
        r = requests.post(f"{base_url}/api/auth/login", data={
            "username": unique_user["username"],
            "password": "wrongpassword",
        })
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# Foods
# ---------------------------------------------------------------------------

class TestFoods:
    def test_list_foods(self, base_url):
        r = requests.get(f"{base_url}/api/foods/", params={"page": 1, "per_page": 5})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert len(data["items"]) <= 5
        assert data["total"] > 0

    def test_list_foods_by_category(self, base_url):
        r = requests.get(f"{base_url}/api/foods/", params={"category": "Fruits and Fruit Juices", "per_page": 3})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] > 0
        for item in data["items"]:
            assert item["category"] == "Fruits and Fruit Juices"

    def test_list_categories(self, base_url):
        r = requests.get(f"{base_url}/api/foods/categories")
        assert r.status_code == 200
        categories = r.json()
        assert isinstance(categories, list)
        assert len(categories) > 10
        assert "Dairy and Egg Products" in categories

    def test_search_foods(self, base_url):
        r = requests.get(f"{base_url}/api/foods/search", params={"q": "apple", "per_page": 5})
        assert r.status_code == 200
        data = r.json()
        assert data["total"] > 0
        # At least one result should contain "apple" (case-insensitive)
        names = [item["name"].lower() for item in data["items"]]
        assert any("apple" in n for n in names)

    def test_search_foods_with_category(self, base_url):
        r = requests.get(f"{base_url}/api/foods/search", params={
            "q": "chicken", "category": "Poultry Products", "per_page": 5,
        })
        assert r.status_code == 200
        data = r.json()
        for item in data["items"]:
            assert item["category"] == "Poultry Products"

    def test_search_empty_query(self, base_url):
        r = requests.get(f"{base_url}/api/foods/search", params={"q": ""})
        assert r.status_code == 422  # min_length=1

    def test_get_food_detail(self, base_url):
        # First get a valid food id
        r = requests.get(f"{base_url}/api/foods/", params={"per_page": 1})
        food_id = r.json()["items"][0]["id"]

        r = requests.get(f"{base_url}/api/foods/{food_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == food_id
        assert "name" in data
        assert "calories" in data

    def test_get_food_not_found(self, base_url):
        r = requests.get(f"{base_url}/api/foods/999999")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Meals (requires auth)
# ---------------------------------------------------------------------------

class TestMeals:
    @pytest.fixture(autouse=True)
    def _setup(self, base_url, auth_headers):
        self.base_url = base_url
        self.headers = auth_headers

    def _get_food_id(self):
        r = requests.get(f"{self.base_url}/api/foods/", params={"per_page": 1})
        return r.json()["items"][0]["id"]

    def test_meal_crud(self):
        food_id = self._get_food_id()
        today = dt.date.today().isoformat()

        # CREATE
        r = requests.post(f"{self.base_url}/api/meals/", headers=self.headers, json={
            "date": today,
            "meal_type": "lunch",
            "notes": "pytest test meal",
            "items": [{"food_id": food_id, "quantity": 150}],
        })
        assert r.status_code == 201, f"Create meal failed: {r.text}"
        meal = r.json()
        meal_id = meal["id"]
        assert meal["meal_type"] == "lunch"
        assert len(meal["items"]) == 1

        # READ single
        r = requests.get(f"{self.base_url}/api/meals/{meal_id}", headers=self.headers)
        assert r.status_code == 200
        assert r.json()["id"] == meal_id

        # UPDATE
        r = requests.put(f"{self.base_url}/api/meals/{meal_id}", headers=self.headers, json={
            "meal_type": "dinner",
            "notes": "updated by pytest",
        })
        assert r.status_code == 200
        assert r.json()["meal_type"] == "dinner"

        # LIST
        r = requests.get(f"{self.base_url}/api/meals/", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] >= 1

        # DELETE
        r = requests.delete(f"{self.base_url}/api/meals/{meal_id}", headers=self.headers)
        assert r.status_code == 204

        # Verify deleted
        r = requests.get(f"{self.base_url}/api/meals/{meal_id}", headers=self.headers)
        assert r.status_code == 404

    def test_create_meal_no_items(self):
        r = requests.post(f"{self.base_url}/api/meals/", headers=self.headers, json={
            "date": dt.date.today().isoformat(),
            "meal_type": "breakfast",
            "items": [],
        })
        assert r.status_code == 422  # min_length=1

    def test_create_meal_future_date(self):
        food_id = self._get_food_id()
        future = (dt.date.today() + dt.timedelta(days=7)).isoformat()
        r = requests.post(f"{self.base_url}/api/meals/", headers=self.headers, json={
            "date": future,
            "meal_type": "breakfast",
            "items": [{"food_id": food_id, "quantity": 100}],
        })
        assert r.status_code == 422

    def test_create_meal_unauthorized(self, base_url):
        r = requests.post(f"{base_url}/api/meals/", json={
            "date": dt.date.today().isoformat(),
            "meal_type": "breakfast",
            "items": [{"food_id": 1, "quantity": 100}],
        })
        assert r.status_code == 401

    def test_get_others_meal(self):
        """Cannot access a non-existent / other user's meal."""
        r = requests.get(f"{self.base_url}/api/meals/999999", headers=self.headers)
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Analytics (requires auth + a meal)
# ---------------------------------------------------------------------------

class TestAnalytics:
    @pytest.fixture(autouse=True)
    def _setup(self, base_url, auth_headers):
        self.base_url = base_url
        self.headers = auth_headers

    def _ensure_meal(self):
        """Create a meal for today so analytics have data."""
        r = requests.get(f"{self.base_url}/api/foods/", params={"per_page": 1})
        food_id = r.json()["items"][0]["id"]
        today = dt.date.today().isoformat()

        requests.post(f"{self.base_url}/api/meals/", headers=self.headers, json={
            "date": today,
            "meal_type": "snack",
            "items": [{"food_id": food_id, "quantity": 100}],
        })

    def test_daily_summary(self):
        self._ensure_meal()
        today = dt.date.today().isoformat()
        r = requests.get(f"{self.base_url}/api/analytics/daily", headers=self.headers, params={"date": today})
        assert r.status_code == 200
        data = r.json()
        assert data["date"] == today
        assert "total" in data
        assert data["total"]["calories"] >= 0

    def test_weekly_trend(self):
        self._ensure_meal()
        start = (dt.date.today() - dt.timedelta(days=6)).isoformat()
        r = requests.get(f"{self.base_url}/api/analytics/weekly", headers=self.headers, params={"start": start})
        assert r.status_code == 200
        data = r.json()
        assert len(data["daily"]) == 7
        assert "average" in data

    def test_balance(self):
        self._ensure_meal()
        today = dt.date.today().isoformat()
        r = requests.get(f"{self.base_url}/api/analytics/balance", headers=self.headers, params={"date": today})
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        # Should have entries for calories, protein, fat, carbs, fiber
        nutrients = {item["nutrient"] for item in data["items"]}
        assert "calories" in nutrients

    def test_analytics_unauthorized(self, base_url):
        r = requests.get(f"{base_url}/api/analytics/daily", params={"date": dt.date.today().isoformat()})
        assert r.status_code == 401


# ---------------------------------------------------------------------------
# User Profile (requires auth)
# ---------------------------------------------------------------------------

class TestUserProfile:
    @pytest.fixture(autouse=True)
    def _setup(self, base_url, auth_headers):
        self.base_url = base_url
        self.headers = auth_headers

    def test_get_profile(self):
        r = requests.get(f"{self.base_url}/api/users/profile", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "username" in data
        assert "email" in data

    def test_update_profile(self):
        r = requests.put(f"{self.base_url}/api/users/profile", headers=self.headers, json={
            "height": 175.0,
            "weight": 70.0,
            "age": 25,
            "gender": "male",
            "activity_level": "moderate",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["height"] == 175.0
        assert data["weight"] == 70.0
        assert data["age"] == 25

    def test_update_profile_partial(self):
        r = requests.put(f"{self.base_url}/api/users/profile", headers=self.headers, json={
            "weight": 72.5,
        })
        assert r.status_code == 200
        assert r.json()["weight"] == 72.5

    def test_update_profile_invalid(self):
        r = requests.put(f"{self.base_url}/api/users/profile", headers=self.headers, json={
            "height": -10,  # invalid
        })
        assert r.status_code == 422

    def test_profile_unauthorized(self, base_url):
        r = requests.get(f"{base_url}/api/users/profile")
        assert r.status_code == 401
