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
    cur_start = cur_end - timedelta(days=cur - 1) if cur else None
    # longest streak
    best, run, best_end, prev = 0, 0, None, None
    for day in sorted(k for k, v in counts.items() if v > 0):
        run = run + 1 if prev and (day - prev).days == 1 else 1
        if run >= best:
            best, best_end = run, day
        prev = day
    best_start = best_end - timedelta(days=best - 1) if best else None
    return dict(total=total, cur=cur, cur_start=cur_start, cur_end=cur_end if cur else None,
                best=best, best_start=best_start, best_end=best_end)

def fmt(d):
    return f"{d.strftime('%b')} {d.day}" if d else "-"

def rng(a, b):
    return f"{fmt(a)} - {fmt(b)}" if a and b else "No active streak"

def render(s, first_day):
    bg, title, text, num, accent = "#1a1b27", "#70a5fd", "#38bdae", "#a9b1d6", "#bf91f3"
    cols = [
        (82, str(s["total"]), "Total Contributions", f"{first_day.strftime('%b')} {first_day.day}, {first_day.year} - Present", num),
        (247, str(s["cur"]), "Current Streak", rng(s["cur_start"], s["cur_end"]), accent),
        (412, str(s["best"]), "Longest Streak", rng(s["best_start"], s["best_end"]), num),
    ]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="170" viewBox="0 0 495 170" role="img" aria-label="GitHub streak">',
             f'<rect width="495" height="170" rx="10" fill="{bg}"/>',
             f'<g font-family="Segoe UI, Ubuntu, Arial, sans-serif" text-anchor="middle">']
    for x, n, label, sub, color in cols:
        parts.append(f'<text x="{x}" y="75" font-size="32" font-weight="700" fill="{color}">{n}</text>')
        parts.append(f'<text x="{x}" y="105" font-size="14" font-weight="600" fill="{title if color != accent else accent}">{label}</text>')
        parts.append(f'<text x="{x}" y="128" font-size="11" fill="{text}">{sub}</text>')
    for x in (165, 330):
        parts.append(f'<line x1="{x}" y1="40" x2="{x}" y2="130" stroke="#3b4261" stroke-width="1"/>')
    parts.append("</g></svg>")
    return "\n".join(parts)

if __name__ == "__main__":
    login = os.environ["GH_LOGIN"]
    token = os.environ["GH_TOKEN"]
    days = fetch_days(login, token)
    stats = compute(days)
    first = date.fromisoformat(min(days))
    os.makedirs("assets", exist_ok=True)
    with open("assets/streak.svg", "w", encoding="utf-8") as f:
        f.write(render(stats, first))
    print(f"total={stats['total']} current={stats['cur']} longest={stats['best']}")
