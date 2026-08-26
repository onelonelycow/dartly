"""
probe_source.py — measure a candidate source by what it adds, not what it holds.

VOLUME IS THE WRONG TEST AND IT IS THE ONE WE KEPT USING. Measured 2026-08-26,
82% of the board came from two sources a member could open themselves —
himalayas at 61.2% and freelancer at 20.9% — and 17 of the 21 sources together
were 2.3%. A source that returns 500 gigs already on the board is worth nothing
to a member and costs a fetcher to maintain. The number that matters is the
share of a source's listings that appear NOWHERE ELSE on the board.

So this fetches a sample, normalises each title, and prints the sample in a form
the overlap query can consume. Deliberately dependency-free: urllib and the
standard library, so it runs anywhere, including a laptop with no virtualenv.

It does not write to the board, add a source, or change any behaviour. It is a
measuring instrument, and the decision it informs — build a fetcher or don't —
stays a human one.

    python3 tools/probe_source.py                 # every candidate
    python3 tools/probe_source.py github mastodon # named ones
"""
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
from html import unescape

sys.path.insert(0, ".")

UA = "Mozilla/5.0 (compatible; Nabbly source probe)"
TIMEOUT = 30


def _ssl_context():
    """
    A verifying context that also works on a Python with no CA bundle wired up.

    A python.org build on macOS ships no cafile, so every https call here failed
    with CERTIFICATE_VERIFY_FAILED while curl against the same URL was fine —
    curl reads the system store, this Python does not. The fix is to hand it the
    same store, NOT to pass an unverified context: this reads third-party
    endpoints over the open internet, and turning verification off to make a
    measuring tool run is how a measuring tool starts measuring a
    man-in-the-middle.
    """
    ctx = ssl.create_default_context()
    if not (ctx.cert_store_stats() or {}).get("x509_ca"):
        for path in ("/etc/ssl/cert.pem", "/usr/local/etc/openssl/cert.pem"):
            if os.path.exists(path):
                ctx.load_verify_locations(cafile=path)
                break
    return ctx


_CTX = _ssl_context()


def _get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "application/json, */*"})
    with urllib.request.urlopen(req, timeout=TIMEOUT, context=_CTX) as r:
        return r.read().decode("utf-8", "replace")


def _json(url: str):
    return json.loads(_get(url))


def _text(html: str) -> str:
    """Tags out, entities decoded, whitespace collapsed."""
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", html or "")).split())


def norm(title: str) -> str:
    """
    The board's own definition of "the same posting", imported rather than
    reimplemented — a second copy here would let the score that justifies a
    source drift away from the rule the board actually applies.
    """
    import classify
    return classify.title_key(title)


# ── candidates ──────────────────────────────────────────────────────────────
# Each returns a list of {title, body, url}. Endpoints verified live on
# 2026-08-26; the ones that did not answer are recorded so nobody re-tests them:
#   bluesky public search  403 from this network
#   journalism.co.uk/jobs  404
#   problogger jobs feed   200 but 833 bytes, an empty feed

def probe_github():
    """Open issues carrying a bounty label: paid work, invisible to job boards."""
    d = _json("https://api.github.com/search/issues?q=label:bounty+state:open"
              "+is:issue&sort=created&order=desc&per_page=100")
    return [{"title": i.get("title") or "",
             "body": _text(i.get("body") or "")[:600],
             "url": i.get("html_url") or ""} for i in d.get("items", [])]


def probe_mastodon():
    """The #hiring tag on mastodon.social: posted by people, not syndicated."""
    d = _json("https://mastodon.social/api/v1/timelines/tag/hiring?limit=40")
    out = []
    for s in d:
        text = _text(s.get("content"))
        if text:
            out.append({"title": text[:120], "body": text, "url": s.get("url") or ""})
    return out


def probe_ukcontracts():
    """
    UK public procurement, open tenders. Free, unauthenticated, and as far as I
    can tell carried by no freelance board anywhere.
    """
    d = _json("https://www.contractsfinder.service.gov.uk/Published/Notices/"
              "OCDS/Search?stages=tender&limit=100")
    out = []
    for r in d.get("releases", []):
        t = r.get("tender") or {}
        val = (t.get("value") or {}).get("amount")
        out.append({"title": t.get("title") or "",
                    "body": (t.get("description") or "")[:600],
                    "url": (r.get("links") or {}).get("self") or "",
                    "value": val})
    return out


PROBES = {"github": probe_github,
          "mastodon": probe_mastodon,
          "ukcontracts": probe_ukcontracts}


def main(names):
    try:
        import classify
    except Exception:
        classify = None

    report = {}
    for name in names:
        try:
            items = PROBES[name]()
        except urllib.error.HTTPError as e:
            print(f"  {name:14} HTTP {e.code} — skipped")
            continue
        except Exception as e:
            print(f"  {name:14} {type(e).__name__}: {e} — skipped")
            continue

        fields, demand = {}, 0
        for it in items:
            if classify:
                tags = classify.classify(it["title"], it.get("body", ""), name)
                if tags["is_demand"]:
                    demand += 1
                fields[tags["job_type"]] = fields.get(tags["job_type"], 0) + 1

        titles = sorted({norm(i["title"]) for i in items if norm(i["title"])})
        report[name] = {"fetched": len(items), "demand": demand,
                        "unique_titles": len(titles), "titles": titles,
                        "fields": dict(sorted(fields.items(),
                                              key=lambda kv: -kv[1])[:6])}
        print(f"  {name:14} {len(items):>4} items   {demand:>4} read as demand   "
              f"{len(titles):>4} distinct titles")
        for f, n in list(report[name]["fields"].items())[:4]:
            print(f"                   {n:>4}  {f}")

    out = "/private/tmp/claude-501/probe.json"
    try:
        with open(out, "w") as f:
            json.dump(report, f, indent=1)
        print(f"\n  titles written to {out} for the overlap query")
    except OSError as e:
        print(f"  ! could not write {out}: {e}")
    return report


if __name__ == "__main__":
    main([a for a in sys.argv[1:] if a in PROBES] or list(PROBES))
