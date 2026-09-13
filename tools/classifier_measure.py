"""Measure the classifier: 300 recent English board rows, judged independently."""
import sys, os, json, sqlite3, random, csv, re, time
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, ".")
import anthropic, config

SP = os.environ["SP"]
CATS = list(config.JOB_TYPES.keys()) + ["Other / general"]
random.seed(20260913)
conn = sqlite3.connect(f"{SP}/f_board2.db"); conn.row_factory = sqlite3.Row
rows = [dict(r) for r in conn.execute(
    "select id, source, title, body, job_type, size_tier from posts "
    "where is_primary=1 and lang_code='en' and sort_at >= datetime('now','-8 days')")]
print("population:", len(rows))
sample = random.sample(rows, 300)

SYSTEM = f"""You label job and freelance-gig postings for a board that files each posting under exactly one category.
The categories (use these exact strings):
{chr(10).join('- ' + c for c in CATS)}

Rules:
- Pick the category that names the WORK BEING HIRED FOR — the role the person would perform — not tools mentioned in passing, not the client's industry, not the company's product.
- "Development / tech" is only for building or maintaining software (code, apps, websites, APIs, automation, AI/ML engineering). A civil/mechanical/electrical role is "Engineering". A site plan, a floor plan or a building is "Architecture / 3D".
- "Management / operations" is for running a team, an office, a company or its operations (head of, director, ops manager, chief of staff), not for a specialist who happens to be senior.
- "Other / general" when nothing fits, or the posting is not a role at all (a talent pool, a spam listing, a product for sale).
- is_opening: true if this is a real posting someone could apply to and be paid for; false if it is a talent pool, "future opportunities", a test row, spam, or a listing selling something.

Reply with ONLY a JSON object, no prose:
{{"category": "<one of the categories>", "confidence": "high"|"medium"|"low", "is_opening": true|false}}"""

client = anthropic.Anthropic()
def judge(r):
    body = re.sub(r"\s+", " ", (r["body"] or ""))[:1200]
    msg = f"Source: {r['source']}\nTitle: {r['title']}\nPosting: {body}"
    for attempt in range(3):
        try:
            resp = client.messages.create(
                model="claude-opus-5", max_tokens=200,
                system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                output_config={"effort": "low"},
                messages=[{"role": "user", "content": msg}])
            text = next(b.text for b in resp.content if b.type == "text")
            m = re.search(r"\{.*\}", text, re.S); j = json.loads(m.group(0))
            if j.get("category") not in CATS: raise ValueError(f"bad category {j.get('category')!r}")
            return {**{k: r[k] for k in ("id", "source", "title", "job_type", "size_tier")},
                    "judge": j["category"], "conf": j.get("confidence", ""), "opening": j.get("is_opening", True),
                    "cache_read": resp.usage.cache_read_input_tokens, "in": resp.usage.input_tokens, "out": resp.usage.output_tokens}
        except (anthropic.RateLimitError, anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            time.sleep(3 * (attempt + 1)); err = e
        except (ValueError, json.JSONDecodeError, StopIteration) as e:
            err = e
    return {**{k: r[k] for k in ("id", "source", "title", "job_type", "size_tier")}, "judge": "ERROR", "conf": str(err)[:80], "opening": None, "cache_read": 0, "in": 0, "out": 0}

t0 = time.time()
with ThreadPoolExecutor(6) as ex: out = list(ex.map(judge, sample))
print(f"judged {len(out)} in {time.time()-t0:.0f}s; errors: {sum(1 for o in out if o['judge']=='ERROR')}; cache hits: {sum(1 for o in out if o['cache_read'])}; tokens in/out: {sum(o['in'] for o in out)}/{sum(o['out'] for o in out)}")
with open(f"{SP}/cls_sample.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print("wrote", f"{SP}/cls_sample.csv")
