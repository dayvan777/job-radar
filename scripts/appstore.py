#!/usr/bin/env python3
"""Optional: refresh public App Store stats for your own iOS app into data/apps.json (doc "app").
Fill APP_ID (the number from the App Store link .../id<APP_ID>), COUNTRY and GENRE below; with an empty
APP_ID the script does nothing and the dashboard hides the app cards.
Sources: iTunes lookup API and the App Store top charts RSS (public, no login).
Keeps one history point per day. Run from the project root: python3 scripts/appstore.py"""
import json, os, sys, datetime, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import db  # noqa: E402

APP_ID = ""           # for example "6804173309"
COUNTRY = "ua"        # App Store country code
GENRE = "6010"        # chart category id, 6010 = Navigation
GENRE_NAME = "Навигация"
SITE = ""             # optional app website
CLAIMS = ""           # optional line from your CV, for example "Top 10 in Navigation, 2,000+ downloads"


def get(url):
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.load(r)


def chart(url):
    # third-party app names may contain U+2014; the project never stores that character
    return [(e["id"]["attributes"]["im:id"], e["im:name"]["label"].replace("\u2014", "-"))
            for e in get(url).get("feed", {}).get("entry", [])]


def rank(entries):
    ids = [i for i, _ in entries]
    return ids.index(APP_ID) + 1 if APP_ID in ids else None


def main():
    if not APP_ID:
        print("appstore skipped: APP_ID not set")
        return
    app = get(f"https://itunes.apple.com/lookup?id={APP_ID}&country={COUNTRY}")["results"][0]
    genre_chart = chart(f"https://itunes.apple.com/{COUNTRY}/rss/topfreeapplications/limit=200/genre={GENRE}/json")
    nav, overall = rank(genre_chart), rank(chart(f"https://itunes.apple.com/{COUNTRY}/rss/topfreeapplications/limit=200/json"))
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    doc = db.load("apps").get("app", {})
    hist = [h for h in doc.get("history", []) if h.get("date") != today]
    hist.append({"date": today, "navRank": nav, "overallRank": overall,
                 "rating": app.get("averageUserRating"), "ratings": app.get("userRatingCount")})
    doc.update({
        "name": app.get("trackName"), "url": app.get("trackViewUrl"), "site": SITE, "claims": CLAIMS,
        "country": COUNTRY.upper(), "genreName": GENRE_NAME,
        "icon": app.get("artworkUrl512") or app.get("artworkUrl100"),
        "version": app.get("version"), "released": (app.get("releaseDate") or "")[:10],
        "updated": (app.get("currentVersionReleaseDate") or "")[:10],
        "rating": app.get("averageUserRating"), "ratings": app.get("userRatingCount"),
        "navRank": nav, "overallRank": overall,
        "navTop": [{"rank": i + 1, "name": n, "self": a == APP_ID} for i, (a, n) in enumerate(genre_chart[:10])],
        "checkedAt": datetime.datetime.now().isoformat(timespec="minutes"),
        "history": hist[-120:],
    })
    data = db.load("apps")
    data["app"] = doc
    db.save("apps", data)
    print(f"ok appstore genre #{nav} overall #{overall} rating {doc['rating']} ({doc['ratings']})")


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:  # network hiccups must never break a run
        print(f"appstore skipped: {ex}")
