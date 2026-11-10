"""
Content-based recommender: represents each attraction by its tag/category
text, vectorizes with TF-IDF, and ranks attractions by cosine similarity to
a user's chosen interests. Also blends in review-derived sentiment and
current popularity so results are not purely tag-matching.
"""
import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

HERE = os.path.dirname(os.path.abspath(__file__))
SPOTS_FILE = os.path.join(HERE, "..", "data", "tourist_spots.csv")


def _load_spots():
    df = pd.read_csv(SPOTS_FILE)
    df["profile_text"] = (
        df["category"].str.lower() + " " + df["tags"].str.replace(",", " ").str.lower()
    )
    return df


def recommend(interests: list[str], top_n: int = 5, sentiment_scores: dict | None = None):
    """
    interests: list of free-text interest keywords, e.g. ["history", "sunset"]
    sentiment_scores: optional {spot_id: avg_sentiment_score} to re-rank by
                       recent visitor sentiment.
    """
    df = _load_spots()
    corpus = df["profile_text"].tolist()

    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(corpus)

    query = " ".join(interests).lower() if interests else ""
    if not query.strip():
        # No interests given -> fall back to popularity ranking
        ranked = df.sort_values("base_popularity", ascending=False)
    else:
        query_vec = vectorizer.transform([query])
        sims = cosine_similarity(query_vec, tfidf_matrix).flatten()
        df = df.copy()
        df["similarity"] = sims

        if sentiment_scores:
            df["sentiment_boost"] = df["id"].astype(str).map(sentiment_scores).fillna(0)
        else:
            df["sentiment_boost"] = 0

        # Weighted score: similarity dominates, sentiment nudges ranking
        df["final_score"] = df["similarity"] * 0.8 + df["sentiment_boost"] * 0.2
        ranked = df.sort_values("final_score", ascending=False)

    cols = ["id", "name", "city", "category", "tags", "avg_rating"]
    return ranked[cols].head(top_n).to_dict(orient="records")
