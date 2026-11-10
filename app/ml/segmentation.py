"""Visitor segmentation with K-Means (documentation section 4.5).

Steps: select numeric features -> StandardScaler -> choose K (silhouette) -> fit K-Means ->
summarise clusters. PCA is used only to draw the 2-D scatter on the dashboard.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from ..constants import CATEGORIES, CATEGORY_COLS

INTEREST_COLS = [CATEGORY_COLS[c] for c in CATEGORIES]
FEATURES = INTEREST_COLS + ["budget_per_day", "trip_days"]
COL_TO_NAME = {v: k for k, v in CATEGORY_COLS.items()}
K_RANGE = range(3, 8)
MIN_RECORDS = 20


class Segmenter:
    def __init__(self, k: int = 0):
        self.k_requested = k
        self.ready = False

    def fit(self, visitors: pd.DataFrame):
        if len(visitors) < MIN_RECORDS:
            self.ready = False
            self.reason = f"Need at least {MIN_RECORDS} visitor records (have {len(visitors)})."
            return self
        df = visitors.reset_index(drop=True)
        X = df[FEATURES].astype(float)
        self.scaler = StandardScaler().fit(X)
        Xs = self.scaler.transform(X)

        scores = {}
        if self.k_requested:
            best_k = int(self.k_requested)
        else:
            for k in K_RANGE:
                if k < len(df):
                    labels = KMeans(k, n_init=10, random_state=42).fit_predict(Xs)
                    scores[k] = float(silhouette_score(Xs, labels))
            best_k = max(scores, key=scores.get)
        self.km = KMeans(best_k, n_init=10, random_state=42).fit(Xs)
        df["cluster"] = self.km.labels_
        self.k = best_k
        self.silhouette = float(silhouette_score(Xs, self.km.labels_)) if best_k > 1 else 0.0
        self.k_scores = scores
        self.n = len(df)
        self.trained_at = pd.Timestamp.now("UTC").strftime("%Y-%m-%d %H:%M UTC")

        self._summarise(df)
        pca = PCA(n_components=2, random_state=42).fit(Xs)
        coords = pca.transform(Xs)
        self.explained = [round(float(v) * 100, 1) for v in pca.explained_variance_ratio_]
        sample = np.random.default_rng(0).permutation(len(df))[:500]
        self.scatter = [{"x": round(float(coords[i, 0]), 3), "y": round(float(coords[i, 1]), 3),
                         "cluster": int(df.at[i, "cluster"])} for i in sample]
        self.ready = True
        return self

    def _summarise(self, df):
        centers = pd.DataFrame(self.scaler.inverse_transform(self.km.cluster_centers_), columns=FEATURES)
        overall = df[INTEREST_COLS].mean()
        q1, q2 = df["budget_per_day"].quantile([1 / 3, 2 / 3])
        summary, used = [], set()
        for c in range(self.k):
            row = centers.loc[c]
            diff = (row[INTEREST_COLS] - overall).sort_values(ascending=False)
            top = [COL_TO_NAME[n] for n in diff.index[:2] if diff[n] > 0.3] or [COL_TO_NAME[diff.index[0]]]
            tier = "Budget" if row["budget_per_day"] < q1 else "Premium" if row["budget_per_day"] > q2 else "Mid-range"
            label = f"{' & '.join(top)} · {tier}"
            if label in used:
                label += f" ({c + 1})"
            used.add(label)
            size = int((df["cluster"] == c).sum())
            summary.append({
                "cluster": c, "label": label, "size": size, "share": round(100 * size / len(df), 1),
                "avg_budget": int(round(row["budget_per_day"], -1)),
                "avg_trip_days": round(float(row["trip_days"]), 1),
                "interests": {COL_TO_NAME[n]: round(float(row[n]), 2) for n in INTEREST_COLS},
                "top_interests": [COL_TO_NAME[n] for n in
                                  row[INTEREST_COLS].sort_values(ascending=False).index[:3]],
            })
        self.summary = summary
        self.labels = {s["cluster"]: s["label"] for s in summary}

    def predict(self, interests, budget, trip_days):
        """interests: iterable of selected category names (scored high); others scored low."""
        if not self.ready:
            return None
        sel = set(interests or [])
        row = {CATEGORY_COLS[c]: (4.5 if c in sel else 1.0) for c in CATEGORIES}
        row["budget_per_day"] = float(budget or self.scaler.mean_[len(INTEREST_COLS)])
        row["trip_days"] = float(trip_days or 5)
        x = self.scaler.transform(pd.DataFrame([row])[FEATURES])
        c = int(self.km.predict(x)[0])
        return {"cluster": c, "label": self.labels[c]}

    def describe(self):
        if not self.ready:
            return {"ready": False, "reason": getattr(self, "reason", "not trained")}
        return {"ready": True, "k": self.k, "silhouette": round(self.silhouette, 3),
                "k_scores": {str(k): round(v, 3) for k, v in self.k_scores.items()},
                "records": self.n, "trained_at": self.trained_at,
                "clusters": self.summary, "scatter": self.scatter, "pca_explained": self.explained}
