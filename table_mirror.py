"""
table_mirror.py — keep a small per-person SQLite table alive across redeploys.

WHY THIS EXISTS: the app's SQLite files sit on Render's ephemeral disk (the
persistent-disk block in render.yaml is commented out), so every redeploy
starts from an empty file. accounts.py and the per-user JSON files already
survive that — they mirror into store.py's durable key-value table. Three
tables did not, and they are exactly the three the product makes promises
about:

  outcomes         every "I got hired!" — the one number a user cannot
                   re-derive, and the input to site_stats()
  match_feedback   every 👍/👎, which is what "it keeps learning from what
                   you rate" actually runs on
  activity         apply clicks, which the weekly digest reports back

Losing those is silent: nothing errors, the counts just quietly read zero and
personalisation reverts to generic.

SHAPE: one durable row per person per table, holding that person's rows as a
JSON list — mirroring the whole person on each write rather than diffing.
These tables are small per user (tens of rows, not thousands), and a
whole-person write is idempotent, so a torn or duplicated write can't corrupt
the result the way a partial row-level sync could. Same trade accounts.py
already makes.

Every function is best-effort and swallows its own errors: a durability
mirror must never be the reason a user's click fails.
"""


def mirror_rows(scope: str, key: str, rows: list[dict]):
    """Push one person's rows for one table into the durable store."""
    if not key:
        return
    try:
        import store
        if store.enabled():
            store.put(scope, str(key), rows)
    except Exception:
        pass


def rehydrate(scope: str, conn, table: str, columns: tuple, is_empty_sql: str):
    """
    Refill an empty local table from the durable store, once.

    Only runs when the local table is EMPTY, so a normal boot with data
    already on disk touches nothing and can never overwrite live rows with a
    stale mirror. Returns how many rows were restored.

    Columns are passed in (rather than SELECT *) so a table that gains a
    column later restores the ones it knows about instead of throwing on an
    arity mismatch — the same reason accounts._rehydrate builds from _COLS.
    """
    try:
        import store
        if not store.enabled():
            return 0
        if conn.execute(is_empty_sql).fetchone()[0] != 0:
            return 0
        saved = store.list_scope(scope)
        if not saved:
            return 0
        placeholders = ",".join("?" for _ in columns)
        collist = ",".join(columns)
        n = 0
        for _key, rows in saved.items():
            if not isinstance(rows, list):
                continue
            for r in rows:
                if not isinstance(r, dict):
                    continue
                conn.execute(
                    f"INSERT OR IGNORE INTO {table} ({collist}) VALUES ({placeholders})",
                    [r.get(c) for c in columns])
                n += 1
        conn.commit()
        return n
    except Exception:
        return 0
