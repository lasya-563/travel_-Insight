"""
A small, dependency-free lexicon-based sentiment scorer for visitor reviews.

This is intentionally simple so the whole project runs offline with no
model downloads. For a production system, swap this module for a
transformer-based classifier (e.g. a fine-tuned DistilBERT / RoBERTa
sentiment model from Hugging Face) without changing the calling code in
app.py -- analyze(text) must keep returning the same dict shape.
"""
import re

POSITIVE_WORDS = {
    "love", "loved", "great", "amazing", "beautiful", "wonderful", "stunning",
    "clean", "friendly", "helpful", "recommend", "magical", "good", "best",
    "excellent", "enjoyed", "worth", "fun", "well", "knowledgeable", "perfect",
    "must-visit", "breathtaking",
}
NEGATIVE_WORDS = {
    "crowded", "poor", "poorly", "disappointed", "dirty", "unhelpful",
    "overpriced", "nightmare", "letdown", "bad", "worst", "urgent",
    "nothing", "average", "queue", "queues", "expensive", "waste",
}

_word_re = re.compile(r"[a-zA-Z']+")


def analyze(text: str) -> dict:
    words = [w.lower() for w in _word_re.findall(text or "")]
    pos_hits = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_hits = sum(1 for w in words if w in NEGATIVE_WORDS)

    score = pos_hits - neg_hits
    if score > 0:
        label = "Positive"
    elif score < 0:
        label = "Negative"
    else:
        label = "Neutral"

    total = max(pos_hits + neg_hits, 1)
    confidence = round(abs(score) / total, 2) if score != 0 else 0.5

    return {
        "label": label,
        "score": score,
        "confidence": confidence,
        "positive_hits": pos_hits,
        "negative_hits": neg_hits,
    }


def batch_analyze(texts):
    return [analyze(t) for t in texts]
