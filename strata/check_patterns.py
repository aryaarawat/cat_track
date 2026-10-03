#!/usr/bin/env python3
"""
Strata layer 3 starter: find patterns in the generated data.

Run after generate_data.py:   python check_patterns.py

What it does, in plain terms:
  1. For every finished repair, look at whether the same warning came back
     on the same machine within 250 operating hours.
       came back      -> "didn't hold"
       didn't         -> "held"
       too recent     -> "pending" (not enough hours have passed to judge)
  2. Group repairs by (machine model, warning code, type of fix) and count
     holds vs. failures. Trust = (holds + 1) / (holds + fails + 2).
  3. Count problems per job-site zone to find location hotspots.
"""
import json
import os
from collections import defaultdict

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
WINDOW = 250
CONFIRMED_AT = 4      # this many judged repairs before a pattern counts as "confirmed"


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


machines = {m["id"]: m for m in load("machines.json")}
faults = load("fault_events.json")
work_orders = {w["id"]: w for w in load("work_orders.json")}
interviews = load("interviews.json")
inspections = load("inspections.json")
zones = {z["id"]: z["name"] for z in load("site.json")["zones"]}

# 1. Verdict for each repair episode
episodes = []
for itv in interviews:
    wo = work_orders[itv["work_order_id"]]
    card = itv["episode_card"]
    mid = itv["machine_id"]
    verdict = "no code to watch"
    for code in card["fault_codes"]:
        later = [f for f in faults if f["machine_id"] == mid and f["code"] == code
                 and f["operating_hours"] > wo["operating_hours_at_close"]]
        nxt = min((f["operating_hours"] for f in later), default=None)
        if nxt is not None and nxt - wo["operating_hours_at_close"] <= WINDOW:
            verdict = "didn't hold"
        elif machines[mid]["current"]["operating_hours"] - wo["operating_hours_at_close"] < WINDOW:
            verdict = "pending"
        else:
            verdict = "held"
    episodes.append({"machine": mid, "model": machines[mid]["model"], "codes": card["fault_codes"],
                     "fix": card["fix_category"], "tech": itv["technician_id"], "verdict": verdict,
                     "date": itv["timestamp"][:10]})

print("REPAIR EPISODES AND VERDICTS")
for e in episodes:
    print(f"  {e['date']}  {e['machine']:<6} model {e['model']:<4} {','.join(e['codes']) or '-':<10} "
          f"{e['fix']:<17} {e['tech']:<9} -> {e['verdict']}")

# 2. Model-level patterns: which fixes work for which warning on which model
groups = defaultdict(lambda: {"held": 0, "didn't hold": 0, "machines": set()})
for e in episodes:
    if e["verdict"] in ("held", "didn't hold"):
        for code in e["codes"]:
            g = groups[(e["model"], code, e["fix"])]
            g[e["verdict"]] += 1
            g["machines"].add(e["machine"])

print("\nSAME-MODEL PATTERNS (trust = (holds+1)/(holds+fails+2))")
for (model, code, fix), g in sorted(groups.items()):
    h, f = g["held"], g["didn't hold"]
    trust = (h + 1) / (h + f + 2)
    label = "confirmed" if h + f >= CONFIRMED_AT else "emerging"
    print(f"  model {model:<4} {code:<9} {fix:<17} held {h}, failed {f}  trust {trust:.0%}  [{label}]  "
          f"on {', '.join(sorted(g['machines']))}")

# 3. Location hotspots
spots = defaultdict(list)
for f in faults:
    if f["severity"] != "low":
        spots[(f["zone"], f["code"])].append(f["machine_id"])
for i in inspections:
    if i["result"] == "issue_found":
        spots[(i["suspected_location_zone"], "tire damage")].append(i["machine_id"])

# A hotspot needs 3+ events AND most of that problem (60%+) happening in one zone.
# Problems spread evenly across the site (like cold-morning warnings) are not about place.
totals = defaultdict(int)
for (zone, what), ms in spots.items():
    totals[what] += len(ms)
print("\nLOCATION HOTSPOTS (3+ events, 60%+ of that problem in one zone)")
for (zone, what), ms in sorted(spots.items(), key=lambda kv: -len(kv[1])):
    share = len(ms) / totals[what]
    if len(ms) >= 3 and share >= 0.6:
        print(f"  {zones[zone]:<22} {what:<12} {len(ms)} events ({share:.0%}) on {', '.join(sorted(set(ms)))}")

# Live situation
print("\nRIGHT NOW")
for m in machines.values():
    c = m["current"]
    if c["status"] in ("Warning", "In repair"):
        print(f"  {m['name']:<15} {c['status']:<9} {zones[c['zone']]:<18} {c['last_update']}")
