#!/usr/bin/env python3
"""
Tekken 8 player lookup using the official ewgf.gg API.
Hit Run in VS Code, paste a Tekken ID (e.g. 3fLQ-T3y9-66qh), get stats
built from that player's recent ranked matches.

Setup:
  1. python3 -m pip install requests
  2. Get a free API key: ewgf.gg -> Settings -> Developer tab
  3. Run the script; it asks for the key once and saves it to ~/.ewgf_key
"""
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests

API = "https://api.ewgf.gg/external"
KEY_FILE = Path.home() / ".ewgf_key"
DEBUG = False  # True prints raw field names from the first battle

CHARACTERS = {
    0: "Paul", 1: "Law", 2: "King", 3: "Yoshimitsu", 4: "Hwoarang", 5: "Xiaoyu", 6: "Jin",
    7: "Bryan", 8: "Kazuya", 9: "Steve", 10: "Jack-8", 11: "Asuka", 12: "Devil Jin",
    13: "Feng", 14: "Lili", 15: "Dragunov", 16: "Leo", 17: "Lars", 18: "Alisa",
    19: "Claudio", 20: "Shaheen", 21: "Nina", 22: "Lee", 23: "Kuma", 24: "Panda",
    28: "Zafina", 29: "Leroy", 32: "Jun", 33: "Reina", 34: "Azucena", 35: "Victor",
    36: "Raven", 38: "Eddy", 39: "Lidia", 40: "Heihachi", 41: "Clive", 42: "Anna",
    43: "Fahkumram", 44: "Armor King",
}
DAN_RANKS = {
    0: "Beginner", 1: "1st Dan", 2: "2nd Dan", 3: "Fighter", 4: "Strategist", 5: "Combatant",
    6: "Brawler", 7: "Ranger", 8: "Cavalry", 9: "Warrior", 10: "Assailant", 11: "Dominator",
    12: "Vanquisher", 13: "Destroyer", 14: "Eliminator", 15: "Garyu", 16: "Shinryu",
    17: "Tenryu", 18: "Mighty Ruler", 19: "Flame Ruler", 20: "Battle Ruler", 21: "Fujin",
    22: "Raijin", 23: "Kishin", 24: "Bushin", 25: "Tekken King", 26: "Tekken Emperor",
    27: "Tekken God", 28: "Tekken God Supreme", 29: "God of Destruction",
}


def char_name(c):
    if isinstance(c, str) and not c.isdigit():
        return c                      # API already gave a name
    try:
        return CHARACTERS.get(int(c), f"Char #{c}")
    except (TypeError, ValueError):
        return "?"


def dan_name(d):
    if isinstance(d, str) and not d.isdigit():
        return d
    try:
        d = int(d)
    except (TypeError, ValueError):
        return "-"
    if d >= 100:
        return "God of Destruction" + (f" {d - 100}" if d > 100 else "")
    return DAN_RANKS.get(d, f"Rank #{d}")


# ------------------------------------------------------------- api key -----
def get_api_key():
    key = os.environ.get("EWGF_API_KEY")
    if key:
        return key.strip()
    if KEY_FILE.exists():
        return KEY_FILE.read_text().strip()
    print("No ewgf.gg API key found. Get a free one at ewgf.gg -> Settings -> Developer.")
    key = input("Paste your API key (starts with ewgf_): ").strip()
    if key:
        KEY_FILE.write_text(key)
        KEY_FILE.chmod(0o600)
        print(f"Saved to {KEY_FILE}\n")
    return key


def fetch_battles(tekken_id, key):
    r = requests.get(f"{API}/battles/{tekken_id}",
                     headers={"Authorization": f"Bearer {key}"}, timeout=20)
    try:
        body = r.json()
    except ValueError:
        raise RuntimeError(f"HTTP {r.status_code}, response wasn't JSON")
    if not r.ok:
        err = body.get("error", {})
        code = err.get("code", f"http_{r.status_code}")
        if code in ("invalid_api_key", "api_key_revoked", "invalid_api_key_format"):
            KEY_FILE.unlink(missing_ok=True)
            raise RuntimeError(f"{err.get('message')}\n(Removed saved key - rerun to enter a new one.)")
        raise RuntimeError(err.get("message", code))
    meta = body.get("_metadata", {})
    data = body.get("data", body)
    if isinstance(data, dict):  # in case battles are nested one level down
        data = next((v for v in data.values() if isinstance(v, list)), [])
    return data, meta


# ------------------------------------------------------ field handling -----
def norm(d):
    """Make keys comparable: player1PolarisId / player1_polaris_id -> player1polarisid"""
    return {k.replace("_", "").lower(): v for k, v in d.items()} if isinstance(d, dict) else {}


def side(b, n, field):
    for k in (f"player{n}{field}", f"p{n}{field}"):
        if k in b:
            return b[k]
    return None


# ----------------------------------------------------------------- stats ---
def show_stats(tekken_id, battles):
    tid = tekken_id.replace("-", "").lower()
    if DEBUG and battles:
        print("  [debug] battle fields:", sorted(battles[0].keys()))

    rows = []
    for raw in battles:
        b = norm(raw)
        p1 = str(side(b, 1, "polarisid") or side(b, 1, "tekkenid") or "").replace("-", "").lower()
        me, opp = (1, 2) if p1 == tid else (2, 1)
        winner = b.get("winner")
        rows.append({
            "name": side(b, me, "name"),
            "char": char_name(side(b, me, "characterid") or side(b, me, "character")),
            "rank": side(b, me, "danrank"),
            "power": side(b, me, "tekkenpower"),
            "opp": side(b, opp, "name"),
            "opp_char": char_name(side(b, opp, "characterid") or side(b, opp, "character")),
            "mine": side(b, me, "roundswon"),
            "theirs": side(b, opp, "roundswon"),
            "won": str(winner) == str(me),
            "date": b.get("date") or b.get("battleat") or b.get("battletime"),
        })

    latest = rows[0]
    print("\n" + "=" * 62)
    print(f"  {latest['name']}   (Tekken ID: {tekken_id})")
    if latest["power"]:
        print(f"  Tekken Power: {int(latest['power']):,}")
    wins = sum(r["won"] for r in rows)
    print(f"  Last {len(rows)} ranked: {wins}W - {len(rows) - wins}L  ({100 * wins / len(rows):.1f}%)")
    print("=" * 62)

    per_char = defaultdict(lambda: {"w": 0, "l": 0, "rank": None})
    matchups = defaultdict(lambda: {"w": 0, "l": 0})
    for r in rows:
        c = per_char[r["char"]]
        c["w" if r["won"] else "l"] += 1
        if c["rank"] is None:
            c["rank"] = r["rank"]     # rows are newest-first, so first seen = current
        matchups[r["opp_char"]]["w" if r["won"] else "l"] += 1

    print(f"\n  {'Character':<14}{'W':>5}{'L':>5}{'Win %':>8}   Rank")
    for name, s in sorted(per_char.items(), key=lambda kv: -(kv[1]["w"] + kv[1]["l"])):
        n = s["w"] + s["l"]
        print(f"  {name:<14}{s['w']:>5}{s['l']:>5}{100 * s['w'] / n:>7.1f}%   {dan_name(s['rank'])}")

    frequent = [(k, v) for k, v in matchups.items() if v["w"] + v["l"] >= 3]
    if frequent:
        frequent.sort(key=lambda kv: kv[1]["w"] / (kv[1]["w"] + kv[1]["l"]))
        print("\n  Matchups (3+ games):")
        for k, v in frequent:
            n = v["w"] + v["l"]
            print(f"    vs {k:<14}{v['w']}-{v['l']}  ({100 * v['w'] / n:.0f}%)")

    print(f"\n  Last {min(10, len(rows))} matches:")
    for r in rows[:10]:
        score = f"{r['mine']}-{r['theirs']}" if r["mine"] is not None else "   "
        print(f"    {'W' if r['won'] else 'L'}  {score}  {r['char']:<11} vs {r['opp_char']:<11}"
              f" ({r['opp']})  {fmt_date(r['date'])}")
    print()


def fmt_date(d):
    if d is None:
        return ""
    try:
        if str(d).isdigit():
            return datetime.fromtimestamp(int(d)).strftime("%b %d %H:%M")
        return datetime.fromisoformat(str(d).replace("Z", "+00:00")).strftime("%b %d %H:%M")
    except ValueError:
        return str(d)


# ------------------------------------------------------------------ main ---
def main():
    key = get_api_key()
    if not key:
        print("Need an API key to continue.")
        return 1
    print("Tekken 8 Player Lookup (ewgf.gg)  -  type 'q' to quit")
    while True:
        try:
            q = input("\nTekken ID: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in ("q", "quit", "exit"):
            break
        tid = q.replace("-", "")
        if not (tid.isalnum() and len(tid) <= 20):
            print("That doesn't look like a Tekken ID (letters/numbers, like 3fLQ-T3y9-66qh).")
            print("Name search isn't available through the ewgf.gg API.")
            continue
        try:
            battles, meta = fetch_battles(tid, key)
            if not battles:
                print("That player has no recent ranked matches.")
            else:
                show_stats(q, battles)
            if meta.get("rate_limit_remaining") is not None:
                print(f"  (API requests left this hour: {meta['rate_limit_remaining']})")
        except (RuntimeError, requests.RequestException) as e:
            print(f"Error: {e}")
    print("Bye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
