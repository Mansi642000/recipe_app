import pandas as pd
import difflib

# Load and clean dataset
df = pd.read_csv("./dataset/indb.csv")

# Drop any empty or unnamed columns (common in CSVs)
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# Rename to standardized columns (only if they exist)
rename_map = {
    "fibre_g": "fibers",
    "unit_serving_energy_kcal": "calories",
    "unit_serving_carb_g": "carbs",
    "unit_serving_protein_g": "proteins",
    "unit_serving_fat_g": "fats",
    "unit_serving_fibre_g": "fibers"
}
df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)

# Clean all nutrient columns (convert to float safely)
for col in df.columns:
    if col != "food_name" and pd.api.types.is_object_dtype(df[col]):
        try:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        except Exception:
            df[col] = 0

# Ensure food_name is lowercase text
if "food_name" in df.columns:
    df["food_name"] = df["food_name"].astype(str).str.lower()
else:
    raise ValueError("❌ 'food_name' column missing in dataset")

# Define known nutrient columns dynamically
nutrient_cols = [col for col in df.columns if col not in ["food_name"]]

# Common plural to singular corrections
plural_map = {
    "tomatoes": "tomato",
    "potatoes": "potato",
    "berries": "berry",
    "carrots": "carrot",
    "onions": "onion",
    "apples": "apple",
}

# === Functions ===
def get_nutrition(food_query):
    food_query = food_query.strip().lower()
    food_query = plural_map.get(food_query, food_query)
    matches = difflib.get_close_matches(food_query, df['food_name'], n=1, cutoff=0.6)
    if matches:
        row = df.loc[df['food_name'] == matches[0]].iloc[0]
        return {col: float(row[col]) if pd.notnull(row[col]) else 0.0 for col in nutrient_cols}
    return {col: 0.0 for col in nutrient_cols}

def calculate_recipe_nutrition(ingredients_list):
    totals = {col: 0.0 for col in nutrient_cols}
    for ing in ingredients_list:
        nutrition = get_nutrition(ing)
        for key in totals.keys():
            totals[key] += nutrition.get(key, 0.0)
    return totals
