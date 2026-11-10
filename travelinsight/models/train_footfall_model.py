"""
Trains a RandomForestRegressor to predict daily visitor footfall for an
attraction given calendar + weather features, then pickles the model
along with its encoders for use by the Flask app.

Run once (or whenever data/footfall_history.csv changes):
    python3 train_footfall_model.py
"""
import os
import pickle

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "..", "data", "footfall_history.csv")
MODEL_FILE = os.path.join(HERE, "footfall_model.pkl")


def main():
    df = pd.read_csv(DATA_FILE)

    season_map = {s: i for i, s in enumerate(sorted(df["season"].unique()))}
    weather_map = {w: i for i, w in enumerate(sorted(df["weather"].unique()))}

    df["season_enc"] = df["season"].map(season_map)
    df["weather_enc"] = df["weather"].map(weather_map)

    feature_cols = [
        "spot_id", "weekday", "is_weekend", "is_holiday",
        "season_enc", "weather_enc",
    ]
    X = df[feature_cols]
    y = df["visitors"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(
        n_estimators=200, max_depth=12, random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)
    print(f"MAE: {mae:.2f} visitors | R^2: {r2:.3f}")

    bundle = {
        "model": model,
        "season_map": season_map,
        "weather_map": weather_map,
        "feature_cols": feature_cols,
    }
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(bundle, f)
    print(f"Saved model bundle to {MODEL_FILE}")


if __name__ == "__main__":
    main()
