#!/usr/bin/env python3
"""
Tekken 8 player lookup (data from ewgf.gg).
Hit Run in VS Code, type a player name or Tekken ID (e.g. 3YrT-MtjN-qqBn), get stats.

Needs:  python3 -m pip install requests
"""
import sys
from datetime import datetime

import requests

API_BASES = ["https://api.ewgf.gg", "https://ewgf.gg/api"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh) fgc-player-lookup/1.0",
           "Accept": "application/json"}

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


def char_name(cid):
    return CHARACTERS.get(cid, f"Char #{cid}")


def dan_name(d):
    if d is None:
        return "-"
    if d >= 100:  # GoD sub-ranks
        return "God of Destruction" + (f" {d - 100}" if d > 100 else "")
    return DAN_RANKS.get(d, f"Rank #{d}")


def api_get(path, params=None):
    last = None
    for base in API_BASES:
        try:
            r = requests.get(base + path, params=params, headers=HEADERS, timeout=20)
            if r.status_code == 404:
                return None
            if r.ok:
                return r.json()
            last = f"HTTP {r.status_code}"
        except (requests.RequestException, ValueError) as e:
            last = str(e)
    raise RuntimeError(f"Couldn't reach ewgf.gg ({last})")


# ------------------------------------------------------------------ search --
def search(query):
    q = query.strip()
    # Tekken IDs are shown as XXXX-XXXX-XXXX but stored without dashes
    if q.count("-") == 2 and len(q.replace("-", "")) == 12:
        q = q.replace("-", "")
    if not q or len(q) >= 20:
        print("Search must be 1-19 characters.")
        return []
    return api_get("/player-stats/search", {"query": q}) or []


def pick_player(results):
    if len(results) == 1:
        return results[0]
    print(f"\nFound {len(results)} players:")
    for i, p in enumerate(results, 1):
        print(f"  {i:>2}. {p.get('name', '?'):<20} {p.get('formattedTekkenId') or p.get('tekkenId', ''):<16}"
              f" {p.get('mostPlayedCharacter') or '':<12} {p.get('danRankName') or p.get('DanRankName') or ''}")
    while True:
        choice = input("Pick a number (Enter to cancel): ").strip()
        if not choice:
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(results):
            return results[int(choice) - 1]
        print("Not a valid number.")


# ------------------------------------------------------------------- stats --
def show_stats(p):
    print("\n" + "=" * 60)
    print(f"  {p.get('name')}   (Tekken ID: {p.get('polarisId')})")
    print(f"  Tekken Power: {p.get('tekkenPower', 0):,}")
    main = p.get("mainCharacterAndRank") or {}
    if main:
        print("  Main: " + ", ".join(f"{k}: {v}" for k, v in main.items()))
    print("=" * 60)

    chars = p.get("playedCharacters") or {}
    if chars:
        print(f"\n  {'Character':<14}{'W':>6}{'L':>6}{'Win %':>8}   Rank")
        ranked = sorted(chars.items(), key=lambda kv: kv[1].get("wins", 0) + kv[1].get("losses", 0),
                        reverse=True)
        for name, s in ranked:
            w, l = s.get("wins", 0), s.get("losses", 0)
            wr = s.get("characterWinrate")
            wr = wr if wr is not None else (100 * w / (w + l) if w + l else 0)
            print(f"  {name:<14}{w:>6}{l:>6}{wr:>7.1f}%   {dan_name(s.get('currentSeasonDanRank'))}")

        top_name, top = ranked[0]
        best, worst = top.get("bestMatchup") or {}, top.get("worstMatchup") or {}
        if best or worst:
            print(f"\n  {top_name} matchups:")
            for label, m in (("Best", best), ("Worst", worst)):
                for opp, rate in m.items():
                    print(f"    {label:<6} vs {opp:<14}{rate:.1f}%")

    battles = p.get("battles") or []
    if battles:
        me = p.get("polarisId")
        print(f"\n  Last {min(10, len(battles))} matches:")
        for b in battles[:10]:
            p1 = b.get("player1PolarisId") == me
            my_char = char_name(b.get("player1CharacterId") if p1 else b.get("player2CharacterId"))
            opp = b.get("player2Name") if p1 else b.get("player1Name")
            opp_char = char_name(b.get("player2CharacterId") if p1 else b.get("player1CharacterId"))
            mine = b.get("player1RoundsWon") if p1 else b.get("player2RoundsWon")
            theirs = b.get("player2RoundsWon") if p1 else b.get("player1RoundsWon")
            won = (b.get("winner") == 1) == p1
            print(f"    {'W' if won else 'L'}  {mine}-{theirs}  {my_char:<11} vs {opp_char:<11} ({opp})"
                  f"  {fmt_date(b.get('date'))}")
    print()


def fmt_date(d):
    if not d:
        return ""
    try:
        if str(d).isdigit():
            return datetime.fromtimestamp(int(d)).strftime("%b %d %H:%M")
        return datetime.fromisoformat(str(d).replace("Z", "+00:00")).strftime("%b %d %H:%M")
    except ValueError:
        return str(d)


# -------------------------------------------------------------------- main --
def main():
    print("Tekken 8 Player Lookup (ewgf.gg)  -  type 'q' to quit")
    while True:
        try:
            query = input("\nPlayer name or Tekken ID: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if query.lower() in ("q", "quit", "exit"):
            break
        try:
            results = search(query)
            if not results:
                print("No players found. (ewgf.gg only knows players who've played ranked recently.)")
                continue
            chosen = pick_player(results)
            if not chosen:
                continue
            pid = chosen.get("tekkenId") or chosen.get("id")
            stats = api_get(f"/player-stats/{pid}")
            if not stats:
                print("Couldn't load that player's stats.")
                continue
            show_stats(stats)
        except RuntimeError as e:
            print(e)
    print("Bye!")


if __name__ == "__main__":
    sys.exit(main())
