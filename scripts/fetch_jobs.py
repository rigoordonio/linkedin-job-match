#!/usr/bin/env python3
"""Fetch recent remote LinkedIn job postings (public guest endpoints, no login).

Usage:
  fetch_jobs.py --keywords "graphic designer" "visual designer" \
                --location Philippines --days 14 --out jobs.json \
                [--exclude sent_ids.json]

Writes a JSON list of {id, url, title, company, location, posted, description}.
"""
import argparse, html, json, re, sys, time, urllib.error, urllib.parse, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
SEARCH = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETAIL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{}"
RETRY_WAITS = (30, 60, 120)  # seconds to wait after each rate-limit response


def get(url):
    """GET a page, waiting and retrying when LinkedIn rate-limits (429/999) or errors (5xx)."""
    for attempt in range(len(RETRY_WAITS) + 1):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if (e.code in (429, 999) or e.code >= 500) and attempt < len(RETRY_WAITS):
                wait = RETRY_WAITS[attempt]
                print(f"HTTP {e.code}, retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def search(keyword, location, days, pages):
    cards = {}
    for page in range(pages):
        q = urllib.parse.urlencode({
            "keywords": keyword, "location": location,
            "f_WT": 2,                      # 2 = remote
            "f_TPR": f"r{days * 86400}",    # posted within N days
            "start": page * 25,
        })
        try:
            body = get(f"{SEARCH}?{q}")
        except Exception:
            if page == 0:
                raise
            break  # keep the pages already fetched
        if not body.strip():
            break
        for card in body.split("<li>")[1:]:
            m = re.search(r'/jobs/view/[^"?]*?-(\d{9,})', card)
            if not m:
                continue
            title = re.search(r'base-search-card__title">(.*?)</h3>', card, re.S)
            company = re.search(r'base-search-card__subtitle">(.*?)</h4>', card, re.S)
            loc = re.search(r'job-search-card__location">(.*?)</span>', card, re.S)
            posted = re.search(r'datetime="([^"]+)"', card)
            cards[m.group(1)] = {
                "id": m.group(1),
                "url": f"https://www.linkedin.com/jobs/view/{m.group(1)}",
                "title": text(title.group(1)) if title else "",
                "company": text(company.group(1)) if company else "",
                "location": text(loc.group(1)) if loc else "",
                "posted": posted.group(1) if posted else "",
            }
        time.sleep(1)
    return cards


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", nargs="+", required=True)
    ap.add_argument("--location", default="Worldwide")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--out", default="jobs.json")
    ap.add_argument("--exclude", help="JSON file with a list of job IDs to skip (already sent)")
    a = ap.parse_args()

    skip = set()
    if a.exclude:
        try:
            skip = set(json.load(open(a.exclude)))
        except FileNotFoundError:
            pass

    jobs, failed = {}, []
    for kw in a.keywords:
        try:
            jobs.update(search(kw, a.location, a.days, a.pages))
        except Exception as e:
            failed.append(kw)
            print(f"search failed for {kw!r}: {e}", file=sys.stderr)
    if failed and len(failed) == len(a.keywords):
        sys.exit("LinkedIn search failed for every keyword; use the web search fallback")
    jobs = {k: v for k, v in jobs.items() if k not in skip}

    for job in jobs.values():
        try:
            body = get(DETAIL.format(job["id"]))
            d = re.search(r"show-more-less-html__markup[^>]*>(.*?)</div>", body, re.S)
            job["description"] = text(d.group(1)) if d else ""
        except Exception as e:
            job["description"] = f"(fetch failed: {e})"
        time.sleep(0.5)

    out = sorted(jobs.values(), key=lambda j: j["posted"], reverse=True)
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print(f"{len(out)} jobs -> {a.out}" + (f" (failed keywords: {', '.join(failed)})" if failed else ""))
    for j in out:
        print(f'{j["posted"]} | {j["title"]} | {j["company"]} | {j["url"]}')


if __name__ == "__main__":
    main()
