import csv, sys, sqlite3, json; sys.path.insert(0, ".")
import classify, config
SP = "/private/tmp/claude-501/-Users-onelonelycow-demand-radar/909bfebd-d621-469c-9d68-28b8c6c263ad/scratchpad"
grp = {s: g for g, subs in config.CATEGORY_GROUPS.items() for s in subs}; conn = sqlite3.connect(f"{SP}/f_board2.db")
for fx, oldf in (("cls_sample.csv", "old_labels.json"), ("cls_validate.csv", "old_labels_validate.json")):
    rows = list(csv.DictReader(open(f"{SP}/{fx}"))); old = json.load(open(f"{SP}/{oldf}")); n = len(rows)
    new = {r["id"]: classify.classify(r["title"], conn.execute("select body from posts where id=?", (r["id"],)).fetchone()[0] or "", r["source"])["job_type"] for r in rows}
    def sc(lab): return (sum(lab[r["id"]] == r["judge"] for r in rows) / n, sum(grp.get(lab[r["id"]], "O") == grp.get(r["judge"], "O") for r in rows) / n, sum(lab[r["id"]] == "Other / general" for r in rows))
    o, w = sc(old), sc(new)
    print(f"{fx:18} n={n}: old exact {o[0]:.0%} group {o[1]:.0%} other {o[2]:3} | new exact {w[0]:.0%} group {w[1]:.0%} other {w[2]:3} | fixes {sum(old[r['id']]!=r['judge'] and new[r['id']]==r['judge'] for r in rows)} regressions {sum(old[r['id']]==r['judge'] and new[r['id']]!=r['judge'] for r in rows)}")
