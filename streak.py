"""Generate assets/streak.svg (current streak, longest streak, total contributions)
from the GitHub GraphQL contribution calendar. Standard library only."""
import json, os, sys, urllib.request
from datetime import date, datetime, timedelta, timezone

API = "https://api.github.com/graphql"

def gql(query, variables, token):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]

def fetch_days(login, token):
    created = gql("query($l:String!){user(login:$l){createdAt}}", {"l": login}, token)["user"]["createdAt"]
    start = datetime.fromisoformat(created.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    q = """query($l:String!,$f:DateTime!,$t:DateTime!){user(login:$l){contributionsCollection(from:$f,to:$t){
      contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}"""
    days = {}
    year = start.year
    while year <= now.year:
        f = max(start, datetime(year, 1, 1, tzinfo=timezone.utc))
        t = min(now, datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc))
        cal = gql(q, {"l": login, "f": f.isoformat(), "t": t.isoformat()}, token)
        weeks = cal["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for w in weeks:
            for d in w["contributionDays"]:
                days[d["date"]] = d["contributionCount"]
        year += 1
    return days

def compute(days, today=None):
    today = today or datetime.now(timezone.utc).date()
    counts = {date.fromisoformat(k): v for k, v in days.items()}
    total = sum(counts.values())
    # current streak: today may still be empty, so start from yesterday in that case
    d = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
    cur, cur_end = 0, d
    while counts.get(d, 0) > 0:
        cur += 1
        d -= timedelta(days=1)
