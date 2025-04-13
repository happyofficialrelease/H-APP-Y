import pandas as pd
from fuzzywuzzy import process

# --- Load Bookbar Menu ---
menu_df = pd.read_excel("impcsv/Bookbar_Menu_Items_With_Ingredients.xlsx")

# --- Load and Combine Macro Data from New CSVs ---
file_paths = [
    "data/FOOD-DATA-GROUP1.csv",
    "data/FOOD-DATA-GROUP2.csv",
    "data/FOOD-DATA-GROUP3.csv",
    "data/FOOD-DATA-GROUP4.csv",
    "data/FOOD-DATA-GROUP5.csv"
]
macro_dfs = [pd.read_csv(path) for path in file_paths]
calories_df = pd.concat(macro_dfs, ignore_index=True)

# --- Clean and Preprocess Macro Data ---
calories_df["food"] = calories_df["food"].str.strip().str.lower()
macro_columns = ["Caloric Value", "Protein", "Fat", "Carbohydrates"]
for col in macro_columns:
    calories_df[col] = pd.to_numeric(calories_df[col], errors='coerce').fillna(0)

# --- Append Custom Macro Data for Common Unmatched Ingredients ---
# These values are estimated. Adjust portions or values as needed.
custom_macros = pd.DataFrame([
    {"food": "nutella", "Caloric Value": 530, "Protein": 6, "Fat": 31, "Carbohydrates": 57},
    {"food": "pesto", "Caloric Value": 450, "Protein": 6, "Fat": 45, "Carbohydrates": 6},
    {"food": "sourdough", "Caloric Value": 260, "Protein": 9, "Fat": 1.5, "Carbohydrates": 52},
    {"food": "raspberry", "Caloric Value": 52, "Protein": 1.2, "Fat": 0.7, "Carbohydrates": 12},
    {"food": "prawns", "Caloric Value": 99, "Protein": 24, "Fat": 1.5, "Carbohydrates": 0},
    {"food": "spices", "Caloric Value": 2, "Protein": 0, "Fat": 0, "Carbohydrates": 0}  # generic low-value estimate
])
calories_df = pd.concat([calories_df, custom_macros], ignore_index=True)

# --- Function to Calculate Macros for a Dish ---
def calculate_macros(ingredients_str, calorie_data, threshold=85):
    total_calories = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_carbs = 0.0
    missing_ingredients = []
    
    # Split ingredient string (by comma) and clean up spacing/capitalization
    ingredients = [i.strip().lower() for i in ingredients_str.split(",") if isinstance(i, str) and i.strip()]
    
    # For ingredients containing "cheese", deduplicate to prevent over-counting.
    final_ingredients = []
    cheese_seen = set()
    for ing in ingredients:
        if "cheese" in ing:
            if ing not in cheese_seen:
                final_ingredients.append(ing)
                cheese_seen.add(ing)
            else:
                # Skip duplicate cheese to avoid inflated values.
                continue
        else:
            final_ingredients.append(ing)
    
    # Get list of food names from macro data
    food_list = calorie_data["food"].tolist()

    # Match each ingredient using fuzzy matching.
    for ing in final_ingredients:
        match_result = process.extractOne(ing, food_list)
        if match_result:
            best_match, score = match_result
            # Only accept the match if score meets our threshold.
            if score >= threshold:
                row = calorie_data[calorie_data["food"] == best_match].iloc[0]
                total_calories += row.get("Caloric Value", 0)
                total_protein += row.get("Protein", 0)
                total_fat += row.get("Fat", 0)
                total_carbs += row.get("Carbohydrates", 0)
            else:
                missing_ingredients.append(ing)
        else:
            missing_ingredients.append(ing)
    
    # NOTE: For baked items and recipes like "Truffle Egg & Mayo" versus "Scrambled Eggs",
    # double-check the portion sizes and ingredient duplication to ensure realistic values.
    return {
        "Estimated Calories": round(total_calories, 2),
        "Protein (g)": round(total_protein, 2),
        "Fat (g)": round(total_fat, 2),
        "Carbs (g)": round(total_carbs, 2),
        "Unmatched Ingredients": ", ".join(missing_ingredients)
    }

# --- Process Each Menu Item ---
results = []
for _, row in menu_df.iterrows():
    item = row["Item Name"]
    ingredients = row["Ingredients"]
    if pd.isna(ingredients):
        continue
    macros = calculate_macros(ingredients, calories_df)
    macros["Item Name"] = item
    macros["Ingredients"] = ingredients
    results.append(macros)

# --- Save the Results ---
results_df = pd.DataFrame(results)
results_df.to_csv("impcsv/bookbar_menu_with_macros.csv", index=False)

print("✅ Saved: bookbar_menu_with_macros.csv")



