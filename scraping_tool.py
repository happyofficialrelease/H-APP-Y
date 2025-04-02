import pandas as pd
import requests
import time

# --------------------------
# Configuration & Constants
# --------------------------

API_KEY = "Iqk6Rq2QobqJI7Q9pvti4BeqUoRDa8bwIiIMk6pg"  # Replace with your valid API key
SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

# Fallback omega-3 content for common foods (grams per 100g)
omega3_content = {
    'salmon': 2.5, 'mackerel': 2.6, 'sardines': 1.4, 'tuna': 0.5,
    'flaxseed': 22.8, 'chia seeds': 17.8, 'walnuts': 9.1, 'soybeans': 1.6,
    'spinach': 0.1, 'brussels sprouts': 0.1, 'avocado': 0.1, 'eggs': 0.1,
    'shrimp': 0.3, 'oysters': 0.7, 'cod': 0.3, 'herring': 1.7,
    'anchovies': 1.4, 'trout': 0.8, 'seaweed': 0.1, 'canola oil': 9.1,
    'olive oil': 0.1, 'fish oil': 70.0, 'krill oil': 30.0, 'algae oil': 35.0
}

# Keywords to determine if a food is processed
processed_keywords = [
    "fried", "soda", "candy", "chips", "burger", "pizza", "syrup",
    "artificial", "sweetener", "preservative", "processed", "snack"
]

# --------------------------
# Helper Functions
# --------------------------

def get_omega3_content(food_name):
    """Return omega-3 content from predefined dictionary if available."""
    food_lower = food_name.lower()
    for key in omega3_content:
        if key in food_lower:
            return omega3_content[key]
    return 0  # Default to 0 if not found

def search_food(food_name):
    """Query the USDA FoodData Central API for nutritional data."""
    params = {
        'api_key': API_KEY,
        'query': food_name,
        'pageSize': 1
    }
    try:
        response = requests.get(SEARCH_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            if data.get('foods'):
                return data['foods'][0]
    except Exception as e:
        print(f"USDA API error: {e}")
    return None

def extract_nutrients(details):
    """
    Extract total calories, carbs, protein, sugar, omega-3 from USDA response.
    If any value is missing, return 0 as default.
    """
    if not details or 'foodNutrients' not in details:
        return {}

    nutrients = {'calories': 0, 'carbs': 0, 'protein': 0, 'sugar': 0, 'omega3': 0}
    
    for nutrient in details['foodNutrients']:
        name = nutrient.get('nutrientName', '').lower()
        value = nutrient.get('value', 0)
        if 'energy' in name and 'kcal' in name:
            nutrients['calories'] = value
        elif 'carbohydrate' in name and 'total' in name:
            nutrients['carbs'] = value
        elif 'protein' in name:
            nutrients['protein'] = value
        elif 'sugar' in name and 'total' in name:
            nutrients['sugar'] = value
        elif 'omega-3' in name or 'omega 3' in name:
            nutrients['omega3'] = value
    
    return nutrients

def is_processed(food_name):
    """Determine if a food item is processed based on keywords."""
    food_lower = food_name.lower()
    return any(keyword in food_lower for keyword in processed_keywords)

# --------------------------
# Main Processing Script
# --------------------------

def process_menu_file(input_file, output_file):
    """
    Reads the input CSV file, queries USDA API for each menu item,
    extracts nutritional information, and saves results to a new CSV.
    """
    try:
        # Load menu items
        df = pd.read_csv(input_file)
        
        if "Menu Items" not in df.columns:
            print("Error: 'Menu Items' column not found in CSV file.")
            return
        
        df['Calories (kcal)'] = 0
        df['Total Carbohydrate (g)'] = 0
        df['Protein (g)'] = 0
        df['Sugar (g)'] = 0
        df['Omega-3 (g)'] = 0
        df['Processed'] = "No"
        
        for index, row in df.iterrows():
            food_name = row['Menu Items']
            details = search_food(food_name)
            
            if details:
                nutrients = extract_nutrients(details)
                df.at[index, 'Calories (kcal)'] = nutrients.get('calories', 0)
                df.at[index, 'Total Carbohydrate (g)'] = nutrients.get('carbs', 0)
                df.at[index, 'Protein (g)'] = nutrients.get('protein', 0)
                df.at[index, 'Sugar (g)'] = nutrients.get('sugar', 0)
                df.at[index, 'Omega-3 (g)'] = nutrients.get('omega3', 0) if nutrients.get('omega3', 0) > 0 else get_omega3_content(food_name)
            
            df.at[index, 'Processed'] = "Yes" if is_processed(food_name) else "No"

            # Avoid overwhelming the API
            time.sleep(1)

        # Save processed data to CSV
        df.to_csv(output_file, index=False)
        print(f"Processed menu saved to: {output_file}")

    except Exception as e:
        print(f"Error processing menu file: {e}")

# --------------------------
# Run the Script
# --------------------------

input_csv = "India_Menu.csv"  # Input file with menu items
output_csv = "Processed_Menu.csv"  # Output file with nutritional details
process_menu_file(input_csv, output_csv)
