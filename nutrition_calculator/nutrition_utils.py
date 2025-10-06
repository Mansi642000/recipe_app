import pandas as pd
import difflib

# Load and clean dataset
df = pd.read_csv("./dataset/indb.csv")

# Drop any empty or unnamed columns
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

# Common plural to singular corrections
plural_map = {
    "tomatoes": "tomato",
    "potatoes": "potato",
    "berries": "berry",
    "carrots": "carrot",
    "onions": "onion",
    "apples": "apple",
}

# Major nutrients we care about
major_nutrients = ['calories', 'proteins', 'fats', 'carbs', 'fibers']

def get_nutrition(food_query):
    # Normalize the query
    food_query = food_query.strip().lower()
    food_query = plural_map.get(food_query, food_query)

    # Fuzzy match to find closest food name
    food_names = df['food_name'].str.lower()
    matches = difflib.get_close_matches(food_query, food_names, n=1, cutoff=0.6)

    if not matches:
        # No match found
        return {k: 0.0 for k in major_nutrients}

    # Get the first matching row
    row = df[food_names == matches[0]].iloc[0]

    nutrition = {}
    for col in major_nutrients:
        try:
            value = row[col]
            if isinstance(value, pd.Series):
                value = value.iloc[0]
            nutrition[col] = float(value) if pd.notnull(value) else 0.0
        except Exception:
            nutrition[col] = 0.0

    return nutrition

def calculate_recipe_nutrition(ingredients_list):
    # Only sum major nutrients
    totals = {k: 0.0 for k in major_nutrients}
    for ing in ingredients_list:
        nutrition = get_nutrition(ing)
        for k in major_nutrients:
            totals[k] += nutrition.get(k, 0.0)
    return totals
