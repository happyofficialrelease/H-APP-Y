import pandas as pd
from sklearn.preprocessing import MinMaxScaler

# --- Load Data ---
df = pd.read_csv("impcsv/bookbar_menu_with_macros.csv")

# --- Classify Veg / Non-Veg ---
non_veg_keywords = ["chicken", "egg", "pork", "fish", "prawn", "meat", "seafood"]
df["Is_NonVeg"] = df["Ingredients"].str.lower().apply(
    lambda x: any(word in x for word in non_veg_keywords)
)
df["Type"] = df["Is_NonVeg"].map({True: "Non-Veg", False: "Veg"})

# --- Helper: check if any keyword exists ---
def contains_any(ingredients, keywords):
    return any(word in ingredients for word in keywords)

df["Ingredients_lower"] = df["Ingredients"].str.lower()

# --- Flags for Disorders ---
lactose_keywords = ["milk", "cheese", "cream", "butter", "paneer", "cream cheese"]
gluten_keywords = ["flour", "bread", "pasta", "sourdough"]

df["Safe_Lactose"] = ~df["Ingredients_lower"].apply(lambda x: contains_any(x, lactose_keywords))
df["Safe_Gluten"] = ~df["Ingredients_lower"].apply(lambda x: contains_any(x, gluten_keywords))
df["Safe_Diabetes"] = df["Carbs (g)"] < 30
df["Safe_PCOS"] = (df["Carbs (g)"] < 35) & (df["Protein (g)"] > 10) & (df["Fat (g)"] < 30)

# --- Health Score Normalization ---
scaler = MinMaxScaler()
df[["Protein_norm", "Fat_norm", "Carbs_norm"]] = scaler.fit_transform(
    df[["Protein (g)", "Fat (g)", "Carbs (g)"]]
)

# --- Health Scores ---
df["Diabetes_Score"] = df["Protein_norm"] - df["Carbs_norm"]
df["PCOS_Score"] = df["Protein_norm"] - df["Carbs_norm"] + 0.5 * (1 - df["Fat_norm"])
df["Lactose_Score"] = df["Protein_norm"] + (1 - df["Fat_norm"])
df["Gluten_Score"] = df["Protein_norm"] + (1 - df["Carbs_norm"])

# --- Justification Generator ---
def generate_justification(row, disorder):
    p, c, f = row["Protein (g)"], row["Carbs (g)"], row["Fat (g)"]
    ingredients = row["Ingredients_lower"]

    if disorder == "Diabetes":
        return f"Recommended for low carbs ({c}g) and decent protein ({p}g) to control blood sugar."
    elif disorder == "PCOS":
        return f"Good protein ({p}g), lower carbs ({c}g), and moderate fat ({f}g) — ideal for hormonal balance."
    elif disorder == "Lactose Intolerance":
        return f"Contains no dairy ingredients like milk, cream, or cheese."
    elif disorder == "Gluten Intolerance":
        return f"Free of gluten sources like bread, flour, or pasta."
    else:
        return "Meets nutritional needs for the disorder."

# --- Function to Get Top Dishes with Justification ---
def get_top_dishes(df, condition_col, score_col, disorder):
    safe = df[df[condition_col]].copy()
    safe["Justification"] = safe.apply(lambda row: generate_justification(row, disorder), axis=1)
    
    top_veg = safe[safe["Type"] == "Veg"].sort_values(by=score_col, ascending=False).head(5)
    top_nonveg = safe[safe["Type"] == "Non-Veg"].sort_values(by=score_col, ascending=False).head(5)
    
    return top_veg[["Item Name", "Ingredients", score_col, "Justification"]], \
           top_nonveg[["Item Name", "Ingredients", score_col, "Justification"]]

# --- Get Top Recommendations with Justifications ---
disorders = {
    "Diabetes": ("Safe_Diabetes", "Diabetes_Score"),
    "PCOS": ("Safe_PCOS", "PCOS_Score"),
    "Lactose Intolerance": ("Safe_Lactose", "Lactose_Score"),
    "Gluten Intolerance": ("Safe_Gluten", "Gluten_Score"),
}

for disorder, (flag, score) in disorders.items():
    print(f"\n🍽️ Top 5 Veg Dishes for {disorder}:")
    top_veg, top_nonveg = get_top_dishes(df, flag, score, disorder)
    print(top_veg.to_string(index=False))

    print(f"\n🍗 Top 5 Non-Veg Dishes for {disorder}:")
    print(top_nonveg.to_string(index=False))
