import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.cluster import KMeans

# --- Load Data ---
df = pd.read_csv("impcsv/bookbar_menu_with_macros.csv")

# --- Clean and Prepare ---
df = df.dropna(subset=["Estimated Calories", "Protein (g)", "Fat (g)", "Carbs (g)"])
df = df[df["Estimated Calories"] > 0]

# --- Infer Veg/Non-Veg ---
def infer_veg_status(item_name):
    item_name = item_name.lower()
    non_veg_keywords = ["chicken", "egg", "fish", "mutton", "prawn", "meat", "ham", "bacon"]
    for keyword in non_veg_keywords:
        if keyword in item_name:
            return "Non-Veg"
    return "Veg"

df["Veg/Non-Veg"] = df["Item Name"].apply(infer_veg_status)

# --- Emotional Scores ---
df["Lean_Score_MCR"] = (df["Protein (g)"] - 0.5 * df["Fat (g)"] - 0.5 * df["Carbs (g)"]) / df["Estimated Calories"]
df["Energy_Score_MCR"] = (df["Carbs (g)"] - 0.5 * df["Fat (g)"]) / df["Estimated Calories"]
df["Satiety_Score_MCR"] = (df["Fat (g)"] - 0.3 * df["Carbs (g)"]) / df["Estimated Calories"]

# --- Normalize Scores ---
scaler = MinMaxScaler()
df[[ "Lean_Score_MCR_norm", "Energy_Score_MCR_norm", "Satiety_Score_MCR_norm"]] = scaler.fit_transform(df[[ "Lean_Score_MCR", "Energy_Score_MCR", "Satiety_Score_MCR"]])

# --- Clustering on Macronutrients ---
macro_data = df[["Protein (g)", "Fat (g)", "Carbs (g)"]].copy()
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
df["Cluster"] = kmeans.fit_predict(macro_data)

# --- Cluster Labeling Logic ---
cluster_labels = []
for i, center in enumerate(kmeans.cluster_centers_):
    protein, fat, carbs = center
    if protein > fat and protein > carbs:
        cluster_labels.append("Lean")
    elif carbs > fat and carbs > protein:
        cluster_labels.append("Energetic")
    elif fat > carbs and fat > protein:
        cluster_labels.append("Satiated")
    else:
        cluster_labels.append("Mixed")

df["Cluster_Label"] = df["Cluster"].map({i: label for i, label in enumerate(cluster_labels)})

# --- Justification Generator ---
def generate_justification(row, mood):
    p, c, f = row["Protein (g)"], row["Carbs (g)"], row["Fat (g)"]
    
    if mood == "Lean":
        return f"High in protein ({p}g) with lower fat ({f}g) and carbs ({c}g), supporting lean muscle and low-calorie goals."
    elif mood == "Energetic":
        return f"Rich in carbs ({c}g) for quick energy, with moderate fat ({f}g) to sustain stamina."
    elif mood == "Satiated":
        return f"High in fat ({f}g) and moderate carbs ({c}g) for long-lasting fullness and comfort."
    else:
        return "Balanced macros for general well-being."

# --- Function to Get Top 5 per Mood and Veg/Non-Veg with Justifications ---
def get_top_5(df, mood, score_col, veg_status):
    if mood in df["Cluster_Label"].unique():
        mood_df = df[(df["Cluster_Label"] == mood) & (df["Veg/Non-Veg"] == veg_status)].copy()
        mood_df["Justification"] = mood_df.apply(lambda row: generate_justification(row, mood), axis=1)
        top = mood_df.sort_values(by=score_col, ascending=False).head(5)
        if top.empty:
            print(f"⚠️ No top {mood} {veg_status} dishes in cluster. Using global fallback.")
            top = df[df["Veg/Non-Veg"] == veg_status].sort_values(by=score_col, ascending=False).head(5)
    else:
        print(f"⚠️ No '{mood}' cluster found. Using global fallback for {veg_status}.")
        top = df[df["Veg/Non-Veg"] == veg_status].sort_values(by=score_col, ascending=False).head(5)
        top["Justification"] = top.apply(lambda row: generate_justification(row, mood), axis=1)
    return top

# --- Get Top Dishes ---
moods = {
    "Lean": "Lean_Score_MCR_norm",
    "Energetic": "Energy_Score_MCR_norm",
    "Satiated": "Satiety_Score_MCR_norm"
}

for mood, score_col in moods.items():
    for veg_type in ["Veg", "Non-Veg"]:
        top_dishes = get_top_5(df, mood, score_col, veg_type)
        emoji = {"Lean": "🥗", "Energetic": "⚡", "Satiated": "🛋️"}[mood]
        print(f"\n{emoji} Top {veg_type} Dishes to Feel {mood}:\n", 
              top_dishes[["Item Name", score_col, "Protein (g)", "Fat (g)", "Carbs (g)", "Justification"]])

# --- Save Final Output ---
df.to_csv("impcsv/bookbar_macros_with_emotional_scores.csv", index=False)
