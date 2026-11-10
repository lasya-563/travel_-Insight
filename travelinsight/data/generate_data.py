"""
Generates synthetic-but-realistic datasets for TravelInsight:
- footfall_history.csv : daily visitor counts per attraction (for ML training)
- reviews.csv          : visitor review text + rating (for sentiment analysis)

Run once: python3 generate_data.py
"""
import csv
import random
import datetime
import os

random.seed(42)

HERE = os.path.dirname(os.path.abspath(__file__))
SPOTS_FILE = os.path.join(HERE, "tourist_spots.csv")
FOOTFALL_FILE = os.path.join(HERE, "footfall_history.csv")
REVIEWS_FILE = os.path.join(HERE, "reviews.csv")

WEATHER_OPTIONS = ["Sunny", "Cloudy", "Rainy", "Hazy"]
SEASON_BY_MONTH = {
    12: "Winter", 1: "Winter", 2: "Winter",
    3: "Summer", 4: "Summer", 5: "Summer", 6: "Summer",
    7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
    10: "Autumn", 11: "Autumn",
}
HOLIDAYS_2025_26 = {
    "01-01", "01-14", "01-26", "03-14", "03-29", "04-10",
    "05-01", "08-15", "08-27", "10-02", "10-20", "10-21",
    "11-01", "12-25",
}

POSITIVE_SNIPPETS = [
    "Absolutely loved the place, the view was breathtaking.",
    "Great experience with family, well maintained and clean.",
    "A must-visit spot, the history and architecture are stunning.",
    "Had a wonderful time, guides were knowledgeable and friendly.",
    "Beautiful location, perfect for photography and evening walks.",
    "Highly recommend visiting during sunset, truly magical.",
    "Well organized, good facilities and helpful staff.",
    "Kids enjoyed it a lot, worth every rupee.",
]
NEUTRAL_SNIPPETS = [
    "It was an okay experience, nothing extraordinary.",
    "Decent place to visit once, could be better maintained.",
    "Average crowd management, took time to get tickets.",
    "Good for a short visit but not much to do after an hour.",
]
NEGATIVE_SNIPPETS = [
    "Very crowded and poorly managed, long queues everywhere.",
    "Disappointed with the cleanliness, needs urgent attention.",
    "Overpriced tickets for what is offered inside.",
    "Parking was a nightmare and staff was unhelpful.",
    "Not worth the hype, quite a letdown honestly.",
]


def generate_footfall():
    with open(SPOTS_FILE) as f:
        spots = list(csv.DictReader(f))

    start = datetime.date(2024, 1, 1)
    end = datetime.date(2025, 12, 31)

    rows = []
    for spot in spots:
        base = int(spot["base_popularity"])
        d = start
        while d <= end:
            weekday = d.weekday()  # 0=Mon
            is_weekend = 1 if weekday >= 5 else 0
            key = d.strftime("%m-%d")
            is_holiday = 1 if key in HOLIDAYS_2025_26 else 0
            season = SEASON_BY_MONTH[d.month]
            weather = random.choices(
                WEATHER_OPTIONS,
                weights=[0.55, 0.2, 0.15, 0.1] if season != "Monsoon" else [0.2, 0.25, 0.45, 0.1],
            )[0]

            visitors = base * 3.0
            if is_weekend:
                visitors *= 1.6
            if is_holiday:
                visitors *= 2.1
            if season == "Winter":
                visitors *= 1.25
            elif season == "Monsoon":
                visitors *= 0.7
            if weather == "Rainy":
                visitors *= 0.6
            elif weather == "Sunny":
                visitors *= 1.1

            visitors *= random.uniform(0.85, 1.15)
            visitors = max(5, int(visitors))

            rows.append({
                "date": d.isoformat(),
                "spot_id": spot["id"],
                "spot_name": spot["name"],
                "weekday": weekday,
                "is_weekend": is_weekend,
                "is_holiday": is_holiday,
                "season": season,
                "weather": weather,
                "visitors": visitors,
            })
            d += datetime.timedelta(days=1)

    with open(FOOTFALL_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {FOOTFALL_FILE}")


def generate_reviews():
    with open(SPOTS_FILE) as f:
        spots = list(csv.DictReader(f))

    rows = []
    rid = 1
    for spot in spots:
        n_reviews = random.randint(10, 18)
        for _ in range(n_reviews):
            bucket = random.choices(["pos", "neu", "neg"], weights=[0.6, 0.22, 0.18])[0]
            if bucket == "pos":
                text = random.choice(POSITIVE_SNIPPETS)
                rating = random.choice([4, 5, 5])
            elif bucket == "neu":
                text = random.choice(NEUTRAL_SNIPPETS)
                rating = 3
            else:
                text = random.choice(NEGATIVE_SNIPPETS)
                rating = random.choice([1, 2])
            rows.append({
                "id": rid,
                "spot_id": spot["id"],
                "spot_name": spot["name"],
                "review_text": text,
                "rating": rating,
            })
            rid += 1

    with open(REVIEWS_FILE, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {REVIEWS_FILE}")


if __name__ == "__main__":
    generate_footfall()
    generate_reviews()
