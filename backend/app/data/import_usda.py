"""
Import USDA SR Legacy food data into the NutriTrack database.

Usage:
    cd backend/
    conda activate nutritrack
    python -m app.data.import_usda
"""

import csv
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Nutrient IDs we care about
NUTRIENT_MAP = {
    1008: "calories",   # Energy (KCAL)
    1003: "protein",    # Protein (G)
    1004: "fat",        # Total lipid/fat (G)
    1005: "carbs",      # Carbohydrate, by difference (G)
    1079: "fiber",      # Fiber, total dietary (G)
}

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / (
    "dataset/sr_legacy/FoodData_Central_sr_legacy_food_csv_2018-04"
)
DB_PATH = Path(__file__).resolve().parent.parent.parent / "nutritrack.db"


def load_categories(data_dir: Path) -> dict[int, str]:
    """Load food_category.csv → {id: description}"""
    categories = {}
    with open(data_dir / "food_category.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            categories[int(row["id"])] = row["description"]
    print(f"  Loaded {len(categories)} categories")
    return categories


def load_foods(data_dir: Path, categories: dict[int, str]) -> list[dict]:
    """Load food.csv → list of food dicts with category name resolved."""
    foods = []
    with open(data_dir / "food.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat_id = int(row["food_category_id"]) if row["food_category_id"] else None
            foods.append({
                "fdc_id": int(row["fdc_id"]),
                "name": row["description"],
                "category": categories.get(cat_id, "Unknown"),
            })
    print(f"  Loaded {len(foods)} foods")
    return foods


def load_nutrients(data_dir: Path) -> dict[int, dict[str, float]]:
    """
    Load food_nutrient.csv, filter to our 5 nutrients.
    Returns {fdc_id: {field_name: amount}}
    """
    nutrients: dict[int, dict[str, float]] = defaultdict(dict)
    matched = 0
    with open(data_dir / "food_nutrient.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nid = int(row["nutrient_id"])
            if nid in NUTRIENT_MAP:
                fdc_id = int(row["fdc_id"])
                field = NUTRIENT_MAP[nid]
                amount = float(row["amount"]) if row["amount"] else 0.0
                nutrients[fdc_id][field] = amount
                matched += 1
    print(f"  Matched {matched} nutrient records for {len(nutrients)} foods")
    return nutrients


def import_data():
    """Main import function."""
    print(f"Data directory: {DATA_DIR}")
    print(f"Database: {DB_PATH}")

    if not DATA_DIR.exists():
        print(f"ERROR: Data directory not found: {DATA_DIR}")
        return

    if not DB_PATH.exists():
        print(f"ERROR: Database not found: {DB_PATH}")
        print("Run 'alembic upgrade head' first.")
        return

    print("\n1. Loading categories...")
    categories = load_categories(DATA_DIR)

    print("\n2. Loading foods...")
    foods = load_foods(DATA_DIR, categories)

    print("\n3. Loading nutrients (this may take a moment)...")
    nutrients = load_nutrients(DATA_DIR)

    print("\n4. Inserting into database...")
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Clear existing food data (idempotent re-import)
    cursor.execute("DELETE FROM foods")

    inserted = 0
    skipped = 0
    for food in foods:
        fdc_id = food["fdc_id"]
        nut = nutrients.get(fdc_id, {})

        # Skip foods with no calorie data
        if "calories" not in nut:
            skipped += 1
            continue

        cursor.execute(
            """INSERT INTO foods (fdc_id, name, category, calories, protein, fat, carbs, fiber, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                fdc_id,
                food["name"],
                food["category"],
                nut.get("calories", 0.0),
                nut.get("protein", 0.0),
                nut.get("fat", 0.0),
                nut.get("carbs", 0.0),
                nut.get("fiber", 0.0),
                now,
            ),
        )
        inserted += 1

    conn.commit()
    conn.close()

    print(f"\n  Done! Inserted {inserted} foods, skipped {skipped} (no calorie data)")
    print(f"  Database: {DB_PATH}")


if __name__ == "__main__":
    import_data()
