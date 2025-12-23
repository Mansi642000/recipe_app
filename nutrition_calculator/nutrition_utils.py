import os
import pandas as pd
import difflib

# === Locate dataset ===
# Works with either ./dataset/indb_clean.csv or ./dataset/indb.csv
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # project root
DATASET_DIR = os.path.join(BASE_DIR, "dataset")

clean_path = os.path.join(DATASET_DIR, "indb_clean.csv")
raw_path = os.path.join(DATASET_DIR, "indb.csv")

if os.path.exists(clean_path):
    dataset_path = clean_path
elif os.path.exists(raw_path):
    dataset_path = raw_path
else:
    raise FileNotFoundError("❌ No dataset found — please place indb.csv in the dataset folder.")

# === Load and Clean Dataset ===
df = pd.read_csv(dataset_path)
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
df.fillna(0, inplace=True)

# Keep only relevant nutrient columns
keep_cols = [
    "food_name",
    "unit_serving_energy_kcal",
    "unit_serving_carb_g",
    "unit_serving_protein_g",
    "unit_serving_fat_g",
    "unit_serving_fibre_g"
]
df = df[[c for c in keep_cols if c in df.columns]].copy()

# Rename to app-standard names
rename_map = {
    "unit_serving_energy_kcal": "calories",
    "unit_serving_carb_g": "carbs",
    "unit_serving_protein_g": "proteins",
    "unit_serving_fat_g": "fats",
    "unit_serving_fibre_g": "fibers"
}
df.rename(columns=rename_map, inplace=True)

# Normalize
df["food_name"] = df["food_name"].astype(str).str.lower()
df = df.fillna(0)

# Clamp unrealistic per-serving values
df["calories"] = df.get("calories", 0).clip(0, 800)
df["proteins"] = df.get("proteins", 0).clip(0, 80)
df["fats"] = df.get("fats", 0).clip(0, 100)
df["carbs"] = df.get("carbs", 0).clip(0, 120)
df["fibers"] = df.get("fibers", 0).clip(0, 25)

major_nutrients = ["calories", "proteins", "fats", "carbs", "fibers"]


# === Core Functions ===
def get_nutrition(food_query: str):
    """Return nutrition data for one ingredient (per serving)."""
    if not food_query or not isinstance(food_query, str):
        return {k: 0.0 for k in major_nutrients}

    food_query = food_query.strip().lower()
    if not food_query:
        return {k: 0.0 for k in major_nutrients}

    # Fuzzy match with tolerance
    food_names = df["food_name"].tolist()
    matches = difflib.get_close_matches(food_query, food_names, n=1, cutoff=0.6)

    if not matches:
        return {k: 0.0 for k in major_nutrients}

    row = df[df["food_name"] == matches[0]].iloc[0]
    return {k: float(row[k]) if k in row else 0.0 for k in major_nutrients}


def calculate_recipe_nutrition(ingredients_list):
    """
    Calculate total nutrition for a list of ingredients.
    Adjusts nutrients based on realistic serving weights.
    """

    # Average realistic portion weights (grams)
    portion_weights = {
        "poha": 80,
        "rice": 100,
        "bread": 30,              # per slice
        "butter": 5,              # per tsp
        "chutney": 15,            # per tbsp
        "cucumber": 50,
        "tomato": 50,
        "onion": 40,
        "capsicum": 40,
        "potato": 60,
        "oil": 5,                 # per tsp
        "peas": 50,
        "carrot": 50,
        "lemon": 10,
        "peanuts": 15,
        "egg": 50,
        "milk": 100,
        "sugar": 5,
    }

    totals = {k: 0.0 for k in major_nutrients}

    for ingredient in ingredients_list:
        if not ingredient.strip():
            continue

        nutrition = get_nutrition(ingredient)
        if not nutrition:
            continue

        # Find a portion weight if available
        portion = 100  # default: 100 g
        for key in portion_weights:
            if key in ingredient.lower():
                portion = portion_weights[key]
                break

        # Scale nutrients relative to 100 g
        scale = portion / 100.0
        for k in major_nutrients:
            totals[k] += nutrition.get(k, 0.0) * scale

    return {k: round(v, 2) for k, v in totals.items()}
