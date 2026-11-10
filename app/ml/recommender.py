"""Content-based recommender: TF-IDF destination vectors + cosine similarity.

Pipeline (matches the project documentation, section 4.4):
  destination attributes -> text "document" -> TF-IDF vector
  user preferences (+ destinations the user liked) -> vector in the same space
  cosine(u, d) -> blend with rating and budget fit -> ranked list
"""
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from ..constants import split_list, tok

W_SIMILARITY, W_RATING, W_BUDGET = 0.75, 0.15, 0.10
BUDGET_TOLERANCE = 1.25          # destinations costing > 125 % of the budget are excluded
LIKED_WEIGHT = 0.5               # influence of destinations the user rated >=4 / saved


def _destination_doc(row) -> str:
    cat = tok(row["category"])
    acts = [tok(a) for a in split_list(row["activities"])]
    tags = [tok(t) for t in split_list(row["tags"])]
    tag_words = [w for t in tags for w in t.split("_")]
    return " ".join([cat] * 3 + acts * 2 + tag_words + [str(row["description"]).lower()])


def _keyword_tokens(text: str):
    return re.findall(r"[a-z]{3,}", (text or "").lower())


class Recommender:
    def __init__(self, destinations):
        """`destinations`: pandas DataFrame with id,name,category,activities,tags,description."""
        self.df = destinations.reset_index(drop=True)
        docs = [_destination_doc(r) for _, r in self.df.iterrows()]
        self.vectorizer = TfidfVectorizer(sublinear_tf=True, token_pattern=r"[a-z_]{2,}",
                                          stop_words="english")
        self.X = self.vectorizer.fit_transform(docs).toarray()
        self.terms = np.array(self.vectorizer.get_feature_names_out())
        self.index = {int(i): n for n, i in enumerate(self.df["id"])}

    # ------------------------------------------------------------------ vectors
    def user_vector(self, prefs: dict, liked_ids=()):
        words = ([tok(i) for i in prefs.get("interests", [])] * 3
                 + [tok(a) for a in prefs.get("activities", [])] * 2
                 + _keyword_tokens(prefs.get("keywords", "")))
        u = self.vectorizer.transform([" ".join(words)]).toarray()[0]
        liked = [self.index[i] for i in liked_ids if i in self.index]
        if liked:
            u = u + LIKED_WEIGHT * self.X[liked].mean(axis=0)
        return u

    def _explain(self, u, idx, k=4):
        contrib = u * self.X[idx]
        order = np.argsort(contrib)[::-1][:k]
        return [self.terms[j].replace("_", " ") for j in order if contrib[j] > 0]

    # --------------------------------------------------------------- recommend
    def recommend(self, prefs: dict, ratings: dict, liked_ids=(), top_n=9):
        """`ratings` maps destination id -> current effective rating (live from the DB)."""
        u = self.user_vector(prefs, liked_ids)
        cos = cosine_similarity(u.reshape(1, -1), self.X)[0] if u.any() else np.zeros(len(self.df))
        cmax = cos.max()
        cos_n = cos / cmax if cmax > 0 else cos

        rating = np.array([ratings.get(int(i), 0.0) for i in self.df["id"]])
        cost = self.df["budget_per_day"].to_numpy(dtype=float)
        budget = prefs.get("budget")
        if budget:
            fit = np.where(cost <= budget, 1.0, np.clip(1 - (cost - budget) / budget, 0, 1))
            allowed = cost <= budget * BUDGET_TOLERANCE
        else:
            fit, allowed = np.ones(len(cost)), np.ones(len(cost), dtype=bool)
        allowed &= rating >= float(prefs.get("min_rating") or 0)

        score = W_SIMILARITY * cos_n + W_RATING * np.clip((rating - 1) / 4, 0, 1) + W_BUDGET * fit
        score = np.where(allowed, score, -1)
        out = []
        for n in np.argsort(score)[::-1][:top_n]:
            if score[n] < 0:
                break
            r = self.df.iloc[n]
            out.append({
                "id": int(r["id"]), "name": r["name"], "state": r["state"], "category": r["category"],
                "activities": split_list(r["activities"]), "budget_per_day": int(r["budget_per_day"]),
                "rating": round(float(rating[n]), 2), "best_season": r["best_season"],
                "description": r["description"],
                "similarity": round(float(cos[n]), 3), "match": int(round(score[n] * 100)),
                "matched_on": self._explain(u, n),
                "within_budget": bool(not budget or cost[n] <= budget),
            })
        return {"results": out, "cold_start": not u.any()}

    def similar(self, dest_id: int, ratings: dict, n=4):
        if dest_id not in self.index:
            return []
        i = self.index[dest_id]
        sims = cosine_similarity(self.X[i].reshape(1, -1), self.X)[0]
        sims[i] = -1
        res = []
        for j in np.argsort(sims)[::-1][:n]:
            r = self.df.iloc[j]
            res.append({"id": int(r["id"]), "name": r["name"], "category": r["category"],
                        "state": r["state"], "similarity": round(float(sims[j]), 3),
                        "rating": round(float(ratings.get(int(r["id"]), 0)), 2)})
        return res
