#!/usr/bin/env python3
"""
Strata synthetic data generator
================================
Creates a fake-but-realistic year of data for one job site so the Strata demo
has something to remember. Everything is SYNTHETIC: machine serials, fault codes
(all start with "SYN-"), people, and coordinates are made up.

Run:   python generate_data.py
Out:   ./data/*.json  (+ telemetry.csv for opening in Excel/Sheets)

Only uses Python's standard library, so there is nothing to install.

The three data layers this feeds:
  1. Technician interviews  -> data/interviews.json
  2. Cloud storage (raw)    -> telemetry, fault events, work orders, inspections
  3. Patterns               -> NOT generated here; computed from 1 + 2 by
                               check_patterns.py (and later by the app).
                               data/answer_key.json lists what was planted so
                               you can test that your pattern code finds it.
"""
import csv
import json
import math
import os
import random
from collections import defaultdict
from datetime import date, datetime, timedelta

SEED = 42                      # same seed = same data every run
START = date(2025, 10, 1)
END = date(2026, 10, 2)        # "today" in the demo
NOW = datetime(2026, 10, 2, 14, 0)
SERVICE_INTERVAL = 250         # operating hours between routine services
SHIFT_START_HOUR = 6.5         # 06:30
SHIFT_LENGTH = 12.0            # hours in the work window
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

rng = random.Random(SEED)

# --------------------------------------------------------------------------
# Site: zones drawn on a 680 x 290 map canvas (matches the map sketch).
# Fictional lat/lng are derived from x/y so you can also use a real map later.
# --------------------------------------------------------------------------
BASE_LAT, BASE_LNG = 40.0500, -88.3500
ZONES = [
    {"id": "pit",   "name": "North pit",             "kind": "work",        "x": 20,  "y": 20,  "w": 230, "h": 120},
    {"id": "road",  "name": "Haul road bend",        "kind": "travel",      "x": 270, "y": 110, "w": 170, "h": 90},
    {"id": "crush", "name": "Crusher and stockpile", "kind": "work",        "x": 460, "y": 20,  "w": 200, "h": 120},
    {"id": "shop",  "name": "Maintenance shop",      "kind": "maintenance", "x": 20,  "y": 170, "w": 230, "h": 100},
    {"id": "wash",  "name": "Wash bay",              "kind": "maintenance", "x": 460, "y": 170, "w": 200, "h": 100},
]
ZONE_BY_ID = {z["id"]: z for z in ZONES}


def to_latlng(x, y):
    return round(BASE_LAT - y * 0.00002, 6), round(BASE_LNG + x * 0.00003, 6)


def point_in_zone(zone_id):
    z = ZONE_BY_ID[zone_id]
    x = rng.uniform(z["x"] + 25, z["x"] + z["w"] - 25)
    y = rng.uniform(z["y"] + 40, z["y"] + z["h"] - 15)
    lat, lng = to_latlng(x, y)
    return {"x": round(x), "y": round(y), "lat": lat, "lng": lng}


# --------------------------------------------------------------------------
# People
# --------------------------------------------------------------------------
TECHNICIANS = [
    {"id": "T-DALE",   "name": "Dale Hughes",  "years_experience": 28, "languages": ["en"],
     "employed_from": "2001-04-02", "employed_until": "2026-08-15", "note": "Retired Aug 2026"},
    {"id": "T-MARIA",  "name": "Maria Lopez",  "years_experience": 12, "languages": ["es", "en"],
     "employed_from": "2014-06-01", "employed_until": None, "note": ""},
    {"id": "T-SAM",    "name": "Sam Patel",    "years_experience": 4,  "languages": ["en"],
     "employed_from": "2022-03-14", "employed_until": None, "note": ""},
    {"id": "T-JORDAN", "name": "Jordan Reed",  "years_experience": 0.7, "languages": ["en"],
     "employed_from": "2026-02-02", "employed_until": None, "note": "New hire"},
]
TECH_BY_ID = {t["id"]: t for t in TECHNICIANS}
OPERATORS = ["O-ANA", "O-BEN", "O-CARLOS", "O-DEE", "O-ELI", "O-FRAN"]


def tech_available(tid, d):
    t = TECH_BY_ID[tid]
    start = date.fromisoformat(t["employed_from"])
    end = date.fromisoformat(t["employed_until"]) if t["employed_until"] else date.max
    return start <= d <= end


def random_tech(d):
    return rng.choice([t["id"] for t in TECHNICIANS if tech_available(t["id"], d)])


# --------------------------------------------------------------------------
# Machines (model numbers are real Cat model names; serials are fake)
# --------------------------------------------------------------------------
MODEL_INFO = {
    "336": {"type": "Excavator",  "fuel_lph": 22, "mean_hours": 8.0},
    "320": {"type": "Excavator",  "fuel_lph": 15, "mean_hours": 7.5},
    "D6":  {"type": "Dozer",      "fuel_lph": 25, "mean_hours": 7.5},
    "980": {"type": "Loader",     "fuel_lph": 28, "mean_hours": 8.5},
    "775": {"type": "Haul truck", "fuel_lph": 45, "mean_hours": 10.5},
}
MACHINES = [
    ("EX-01", "Excavator #1", "336", "pit",   3120),
    ("EX-03", "Excavator #3", "336", "pit",   5480),
    ("EX-07", "Excavator #7", "336", "pit",   2210),
    ("EX-08", "Excavator #8", "336", "pit",   4060),
    ("EX-10", "Excavator #10", "320", "crush", 6890),
    ("DZ-02", "Dozer #2",     "D6",  "pit",   7350),
    ("DZ-06", "Dozer #6",     "D6",  "pit",   3900),
    ("LD-04", "Loader #4",    "980", "crush", 8120),
    ("LD-05", "Loader #5",    "980", "crush", 5530),
    ("HT-09", "Haul truck #9",  "775", "road", 9870),
    ("HT-11", "Haul truck #11", "775", "road", 11240),
    ("HT-12", "Haul truck #12", "775", "road", 7720),
    ("HT-14", "Haul truck #14", "775", "road", 6010),
]
machines = []
for mid, name, model, home, hrs in MACHINES:
    machines.append({
        "id": mid, "name": name, "make": "CAT", "model": model,
        "type": MODEL_INFO[model]["type"],
        "serial_number": f"SYN{model}{mid.replace('-', '')}",
        "home_zone": home, "operating_hours_at_start": hrs,
    })
MACHINE_BY_ID = {m["id"]: m for m in machines}

# --------------------------------------------------------------------------
# Fault code catalog (synthetic codes; real Cat codes are not used)
# --------------------------------------------------------------------------
FAULT_CODES = {
    "SYN-E214": {"description": "Boom position sensor signal erratic", "severity": "medium", "system": "electrical"},
    "SYN-E412": {"description": "Sensor circuit intermittent, possible moisture", "severity": "medium", "system": "electrical"},
    "SYN-A330": {"description": "DEF dosing system warning", "severity": "medium", "system": "aftertreatment"},
    "SYN-H520": {"description": "Final drive oil level low, leak suspected", "severity": "high", "system": "powertrain"},
    "SYN-T610": {"description": "Tire pressure low", "severity": "medium", "system": "tires"},
    "SYN-G101": {"description": "Low fuel level", "severity": "low", "system": "fuel"},
    "SYN-G105": {"description": "Idle shutdown timer triggered", "severity": "low", "system": "engine"},
    "SYN-G110": {"description": "Air filter restriction", "severity": "low", "system": "engine"},
}

# --------------------------------------------------------------------------
# Forced conditions for planted stories (set before simulating telemetry)
# --------------------------------------------------------------------------
forced_work = set()            # (machine_id, date) that must be a worked day
forced_zone = {}               # (machine_id, date) -> zone id
forced_wash = set()            # (machine_id, date) with a wash bay visit

E214_STARTS = {"EX-01": datetime(2025, 10, 14, 9, 30), "EX-03": datetime(2025, 12, 9, 10, 50),
               "EX-08": datetime(2026, 2, 3, 8, 40), "EX-01b": datetime(2026, 6, 10, 11, 5)}
WASH_CASES = [("DZ-06", datetime(2026, 5, 19, 10, 0)), ("LD-05", datetime(2026, 7, 22, 9, 15)),
              ("DZ-02", datetime(2026, 9, 10, 11, 30))]
TIRE_CASES = [("HT-09", date(2026, 7, 8)), ("HT-12", date(2026, 8, 12)), ("HT-14", date(2026, 9, 16))]

for key, dt in E214_STARTS.items():
    forced_work.add((key[:5], dt.date()))
for mid, dt in WASH_CASES:
    forced_work.add((mid, dt.date()))
    forced_wash.add((mid, dt.date()))
for mid, d in TIRE_CASES:
    forced_work.add((mid, d - timedelta(days=1)))
    forced_zone[(mid, d - timedelta(days=1))] = "road"
# Today
for mid in ["EX-07", "DZ-06", "HT-11", "EX-03"]:
    forced_work.add((mid, END))
forced_wash.add(("DZ-06", END))

# --------------------------------------------------------------------------
# Layer 2a: daily telemetry (shaped like ISO 15143-3 / AEMP 2.0 fields)
# --------------------------------------------------------------------------
def daterange(a, b):
    d = a
    while d <= b:
        yield d
        d += timedelta(days=1)


weather = {}
for d in daterange(START, END):
    doy = d.timetuple().tm_yday
    mean = 11 - 14 * math.cos(2 * math.pi * (doy - 15) / 365) + rng.gauss(0, 3)
    weather[d] = (round(mean - 6, 1), round(mean + 6, 1))   # (low, high) in C

telemetry = {}   # machine_id -> {date: row}
for m in machines:
    mid, info = m["id"], MODEL_INFO[m["model"]]
    hours = float(m["operating_hours_at_start"])
    idle_total = round(hours * 0.18, 1)
    telemetry[mid] = {}
    for d in daterange(START, END):
        weekend = d.weekday() >= 5
        p_work = 0.35 if weekend else (0.92 if info["type"] == "Haul truck" else 0.85)
        worked = (mid, d) in forced_work or rng.random() < p_work
        op = min(SHIFT_LENGTH, max(2.0, rng.gauss(info["mean_hours"], 1.2))) if worked else 0.0
        if d == END:
            op *= (14 - SHIFT_START_HOUR) / SHIFT_LENGTH   # today is "as of 14:00"
        op = round(op, 1)
        idle = round(op * rng.uniform(0.12, 0.3), 1) if worked else 0.0
        if (mid, d) in forced_zone:
            zone = forced_zone[(mid, d)]
        elif info["type"] == "Haul truck":
            zone = rng.choices(["road", "pit", "crush"], weights=[5, 3, 2])[0]
        else:
            zone = m["home_zone"]
        washed = (mid, d) in forced_wash or (worked and info["type"] != "Haul truck" and rng.random() < 0.08)
        low, high = weather[d]
        start_h = hours
        hours = round(hours + op, 1)
        idle_total = round(idle_total + idle, 1)
        pos = point_in_zone(zone)
        telemetry[mid][d] = {
            "date": d.isoformat(), "machine_id": mid,
            "worked": worked,
            "operating_hours_today": op,
            "cumulative_operating_hours_start": round(start_h, 1),
            "cumulative_operating_hours": hours,
            "cumulative_idle_hours": idle_total,
            "fuel_used_last_24h_l": round(op * info["fuel_lph"] * rng.uniform(0.85, 1.15), 1),
            "fuel_remaining_ratio": round(rng.uniform(0.2, 0.95), 2),
            "engine_condition": "running" if worked else "off",
            "avg_load_pct": round(rng.uniform(45, 85), 0) if worked else 0,
            "ambient_low_c": low, "ambient_high_c": high,
            "zone": zone, "washed_today": washed,
            "lat": pos["lat"], "lng": pos["lng"],
        }


def row(mid, d):
    return telemetry[mid][d]


def hours_at(mid, dt):
    """Cumulative operating hours at a given moment."""
    r = row(mid, dt.date())
    start = datetime.combine(dt.date(), datetime.min.time()) + timedelta(hours=SHIFT_START_HOUR)
    frac = (dt - start).total_seconds() / (SHIFT_LENGTH * 3600)
    frac = max(0.0, min(1.0, frac))
    full_day_op = r["operating_hours_today"] if dt.date() != END else r["operating_hours_today"] * SHIFT_LENGTH / (14 - SHIFT_START_HOUR)
    return round(min(r["cumulative_operating_hours"], r["cumulative_operating_hours_start"] + frac * full_day_op), 1)


def dt_at_hours(mid, target):
    """First moment a machine reaches a cumulative operating-hours value."""
    for d in daterange(START, END):
        r = row(mid, d)
        if r["operating_hours_today"] > 0 and r["cumulative_operating_hours_start"] <= target <= r["cumulative_operating_hours"]:
            frac = (target - r["cumulative_operating_hours_start"]) / r["operating_hours_today"]
            dt = datetime.combine(d, datetime.min.time()) + timedelta(hours=SHIFT_START_HOUR + frac * min(SHIFT_LENGTH, r["operating_hours_today"] + 1))
            return dt.replace(second=0, microsecond=0)
    raise ValueError(f"{mid} never reaches {target} hours in range")


# --------------------------------------------------------------------------
# Routine services every 250 hours (Layer 2b: work orders)
# --------------------------------------------------------------------------
fault_events, work_orders, interviews, inspections = [], [], [], []
service_hours = {m["id"]: [] for m in machines}


def next_id(prefix, items, width=4):
    return f"{prefix}-{len(items) + 1:0{width}d}"


for m in machines:
    mid = m["id"]
    due = (int(m["operating_hours_at_start"] // SERVICE_INTERVAL) + 1) * SERVICE_INTERVAL
    service_hours[mid].append(due - SERVICE_INTERVAL)
    for d in daterange(START, END - timedelta(days=1)):
        r = row(mid, d)
        while r["cumulative_operating_hours"] >= due:
            opened = datetime.combine(d, datetime.min.time()) + timedelta(hours=17, minutes=30)
            work_orders.append({
                "id": next_id("WO", work_orders), "machine_id": mid, "type": "service",
                "title": f"{SERVICE_INTERVAL}-hour service", "status": "closed",
                "opened": opened.isoformat(), "closed": (opened + timedelta(minutes=95)).isoformat(),
                "technician_id": random_tech(d), "fault_event_ids": [],
                "operating_hours_at_close": due, "labor_minutes": 95, "parts": ["Oil filter", "Fuel filter"],
            })
            service_hours[mid].append(due)
            due += SERVICE_INTERVAL


def hours_since_service(mid, h):
    past = [s for s in service_hours[mid] if s <= h]
    return round(h - max(past), 1) if past else None


# --------------------------------------------------------------------------
# Fault events, repairs, and interviews (Layers 1 and 2)
# --------------------------------------------------------------------------
def add_fault(mid, code, dt, zone=None):
    r = row(mid, dt.date())
    h = hours_at(mid, dt)
    zone = zone or r["zone"]
    pos = point_in_zone(zone)
    ev = {
        "id": next_id("F", fault_events, 5), "machine_id": mid, "code": code,
        "description": FAULT_CODES[code]["description"], "severity": FAULT_CODES[code]["severity"],
        "timestamp": dt.isoformat(), "operating_hours": h, "zone": zone,
        "lat": pos["lat"], "lng": pos["lng"],
        "context": {
            "ambient_temp_c": r["ambient_low_c"] if dt.hour < 9 else r["ambient_high_c"],
            "avg_load_pct": r["avg_load_pct"],
            "hours_since_service": hours_since_service(mid, h),
            "washed_today": r["washed_today"],
        },
    }
    fault_events.append(ev)
    return ev


# What each kind of fix sounds like in an interview, and what the episode card says.
FIXES = {
    "sensor_swap": {
        "minutes": 75, "parts": ["Boom position sensor"],
        "symptom": "Warning light comes and goes, worse with the boom raised",
        "ruled_out": ["Fault history reviewed"],
        "fix": "Replaced boom position sensor",
        "cause": "Failed sensor (suspected)",
        "answers": ["Boom sensor warning was flickering on and off. Operator said it was worse with the boom up.",
                    "Pulled the code history, didn't really check much else.",
                    "Swapped the boom position sensor. Warning cleared."],
        "answers_es": ["La alerta del sensor del brazo se prendía y se apagaba. El operador dijo que era peor con el brazo arriba.",
                       "Revisé el historial de códigos, nada más.",
                       "Cambié el sensor de posición del brazo. La alerta se quitó."],
    },
    "harness_reroute": {
        "minutes": 110, "parts": ["Harness clamp spacer", "Heat-shrink sleeve"],
        "symptom": "Intermittent boom sensor warning, worse with the boom raised",
        "ruled_out": ["Sensor tested within spec", "Connector pins clean and tight"],
        "fix": "Repaired chafed harness at boom clamp; rerouted and re-clamped with spacer",
        "cause": "Wire harness rubbing against boom clamp",
        "answers": ["Same boom sensor warning. It only shows when the boom is up, so I figured it's movement, not the sensor.",
                    "Tested the sensor, it was in spec. Connector pins were clean.",
                    "Harness was rubbing through at the clamp halfway up the boom. Patched it, rerouted it, put a spacer in the clamp. On these 336s, check that clamp first."],
    },
    "connector_dry": {
        "minutes": 50, "parts": ["Dielectric grease"],
        "symptom": "Sensor circuit warning shortly after pressure washing",
        "ruled_out": ["Sensor tested within spec", "No damaged wiring found"],
        "fix": "Dried and cleaned connector, applied dielectric grease, reseated",
        "cause": "Water in connector from pressure washing",
        "answers": ["Warning popped up right after it came out of the wash bay.",
                    "Sensor was fine, wiring looked fine.",
                    "Water in the connector. Blew it dry, greased it, reseated it. Tell the wash crew to go easy on that harness."],
    },
    "final_drive_seal": {
        "minutes": 300, "parts": ["Final drive seal kit", "Final drive oil"],
        "symptom": "Final drive oil low warning, oil residue on rim",
        "ruled_out": ["Drain plug tight", "No cracks in housing"],
        "fix": "Replaced final drive seal and refilled oil",
        "cause": "Worn final drive seal",
        "answers": ["Oil low warning on the final drive, oil all over the inside of the rim.",
                    "Drain plug was tight, housing had no cracks.",
                    "Seal was worn. Replaced the seal kit and refilled."],
    },
    "tire_replace": {
        "minutes": 150, "parts": ["Tire (775 spec)"],
        "symptom": "Sidewall cut found on pre-shift inspection",
        "ruled_out": ["Rim undamaged", "Other tires fine"],
        "fix": "Replaced damaged tire",
        "cause": "Rock spill on inside of haul road bend",
        "answers": ["Cut in the sidewall on the inside tire. Operator says they ran the haul road bend last shift.",
                    "Rim's fine, other tires are fine.",
                    "Swapped the tire. That's not the first one from that bend, there's rock spilling off loaded trucks on the inside of the curve."],
    },
    "def_check": {
        "minutes": 45, "parts": [],
        "symptom": "DEF warning on cold morning start",
        "ruled_out": ["DEF fluid quality OK", "DEF heater relay OK"],
        "fix": "No fault found; warning cleared after warm-up",
        "cause": "Cold-start condition (suspected)",
        "answers": ["DEF warning first thing in the morning, it was freezing out.",
                    "Checked the fluid and the heater relay, both fine.",
                    "Didn't replace anything. It cleared once the truck warmed up."],
    },
}
QUESTIONS = ["What did you notice when you got to the machine?",
             "What did you check that turned out fine?",
             "What actually fixed it?"]


def add_repair(mid, faults, tech, kind, opened, spanish=False):
    f = FIXES[kind]
    closed = opened + timedelta(minutes=f["minutes"] + rng.randint(-10, 20))
    h_close = hours_at(mid, closed)
    wo = {
        "id": next_id("WO", work_orders), "machine_id": mid, "type": "repair",
        "title": f["symptom"], "status": "closed",
        "opened": opened.isoformat(), "closed": closed.isoformat(),
        "technician_id": tech, "fault_event_ids": [x["id"] for x in faults],
        "operating_hours_at_close": h_close, "labor_minutes": f["minutes"], "parts": f["parts"],
    }
    work_orders.append(wo)
    answers = f["answers_es"] if spanish else f["answers"]
    transcript = []
    for q, a in zip(QUESTIONS, answers):
        transcript += [{"speaker": "Strata", "text": q}, {"speaker": TECH_BY_ID[tech]["name"], "text": a}]
    interviews.append({
        "id": next_id("INT", interviews), "work_order_id": wo["id"], "machine_id": mid,
        "technician_id": tech, "timestamp": (closed + timedelta(minutes=5)).isoformat(),
        "language": "es" if spanish else "en",
        "transcript": transcript,
        "episode_card": {
            "symptom": f["symptom"], "ruled_out": f["ruled_out"], "fix": f["fix"],
            "fix_category": kind, "parts": f["parts"], "suspected_cause": f["cause"],
            "fault_codes": sorted({x["code"] for x in faults}),
            "zone": faults[0]["zone"] if faults else row(mid, opened.date())["zone"],
            "labor_minutes": f["minutes"], "technician_confirmed": True,
        },
    })
    return wo, closed


def plant_chain(mid, first_dt, code, steps):
    """steps: list of (technician, fix kind, recur_after_hours or None, spanish)."""
    fault_dt = first_dt
    for tech, kind, recur, spanish in steps:
        f = add_fault(mid, code, fault_dt)
        _, closed = add_repair(mid, [f], tech, kind, fault_dt + timedelta(minutes=rng.randint(60, 150)), spanish)
        if recur:
            fault_dt = dt_at_hours(mid, hours_at(mid, closed) + recur)


# Story 1: boom sensor warning on model 336 excavators.
# Swapping the sensor never holds; rerouting the harness always does.
plant_chain("EX-01", E214_STARTS["EX-01"], "SYN-E214",
            [("T-SAM", "sensor_swap", 85, False), ("T-DALE", "harness_reroute", None, False)])
plant_chain("EX-03", E214_STARTS["EX-03"], "SYN-E214",
            [("T-DALE", "harness_reroute", None, False)])
plant_chain("EX-08", E214_STARTS["EX-08"], "SYN-E214",
            [("T-MARIA", "sensor_swap", 120, True), ("T-MARIA", "sensor_swap", 60, False),
             ("T-DALE", "harness_reroute", None, False)])
plant_chain("EX-01", E214_STARTS["EX-01b"], "SYN-E214",
            [("T-JORDAN", "sensor_swap", 95, False), ("T-DALE", "harness_reroute", None, False)])
# Model 320 had the code once; a sensor swap held there (different model, different weak spot).
f320 = add_fault("EX-10", "SYN-E214", datetime(2026, 4, 21, 13, 10))
add_repair("EX-10", [f320], "T-SAM", "sensor_swap", datetime(2026, 4, 21, 14, 30))

# Story 2: wash bay moisture (emerging pattern, 3 cases across models)
for (mid, wash_dt), tech in zip(WASH_CASES, ["T-MARIA", "T-SAM", "T-JORDAN"]):
    f = add_fault(mid, "SYN-E412", wash_dt + timedelta(minutes=25), zone="wash")
    add_repair(mid, [f], tech, "connector_dry", wash_dt + timedelta(minutes=90))

# Story 3: tire cuts at the haul road bend (found on inspections)
tire_findings = {}
for (mid, d), tech in zip(TIRE_CASES, ["T-SAM", "T-MARIA", "T-JORDAN"]):
    tire_findings[(mid, d)] = "Sidewall cut on inside rear tire"
    faults = []
    if mid == "HT-12":
        faults.append(add_fault(mid, "SYN-T610", datetime.combine(d - timedelta(days=1), datetime.min.time()) + timedelta(hours=15, minutes=20), zone="road"))
    wo, _ = add_repair(mid, faults, tech, "tire_replace", datetime.combine(d, datetime.min.time()) + timedelta(hours=8))
    interviews[-1]["episode_card"]["zone"] = "road"

# Story 4: DEF warnings on freezing mornings (a condition pattern, not a broken part)
def_faults = []
for m in machines:
    if m["type"] != "Haul truck":
        continue
    for d in daterange(START, END):
        r = row(m["id"], d)
        if r["worked"] and r["ambient_low_c"] < -6 and rng.random() < 0.2:
            dt = datetime.combine(d, datetime.min.time()) + timedelta(hours=6, minutes=rng.randint(50, 85))
            def_faults.append(add_fault(m["id"], "SYN-A330", dt))
by_truck = defaultdict(list)
for f in def_faults:
    by_truck[f["machine_id"]].append(f)
for mid in sorted(by_truck)[:3]:          # one checked-and-nothing-found repair on 3 different trucks
    f = rng.choice(by_truck[mid])
    dt = datetime.fromisoformat(f["timestamp"])
    add_repair(mid, [f], random_tech(dt.date()), "def_check", dt + timedelta(minutes=40))

# Story 5: HT-11 final drive seal. Fixed ~900 hours ago (held), leaking again today.
ht11_now = hours_at("HT-11", NOW)
seal_dt = dt_at_hours("HT-11", ht11_now - 900)
f = add_fault("HT-11", "SYN-H520", seal_dt)
add_repair("HT-11", [f], "T-MARIA", "final_drive_seal", seal_dt + timedelta(minutes=70))

# Background noise: minor faults that need no repair
for m in machines:
    for d in daterange(START, END - timedelta(days=1)):
        r = row(m["id"], d)
        if r["worked"] and rng.random() < 0.04:
            code = rng.choice(["SYN-G101", "SYN-G105", "SYN-G110"])
            add_fault(m["id"], code, datetime.combine(d, datetime.min.time()) + timedelta(hours=rng.uniform(7, 17)))

# --------------------------------------------------------------------------
# Today (2026-10-02, as of 14:00): the live situation the demo opens on
# --------------------------------------------------------------------------
add_fault("EX-07", "SYN-E214", datetime(2026, 10, 2, 10, 12), zone="pit")
add_fault("EX-07", "SYN-E214", datetime(2026, 10, 2, 13, 40), zone="pit")
add_fault("DZ-06", "SYN-E412", datetime(2026, 10, 2, 13, 20), zone="wash")
leak_today = add_fault("HT-11", "SYN-H520", datetime(2026, 10, 2, 8, 15), zone="road")
work_orders.append({
    "id": next_id("WO", work_orders), "machine_id": "HT-11", "type": "repair",
    "title": "Final drive oil low warning, oil residue on rim", "status": "open",
    "opened": "2026-10-02T09:00:00", "closed": None, "expected_done": "2026-10-02T15:00:00",
    "technician_id": "T-MARIA", "fault_event_ids": [leak_today["id"]],
    "operating_hours_at_close": None, "labor_minutes": None, "parts": [],
})
work_orders.append({
    "id": next_id("WO", work_orders), "machine_id": "EX-03", "type": "service",
    "title": f"{SERVICE_INTERVAL}-hour service", "status": "open", "progress_pct": 70,
    "opened": "2026-10-02T11:00:00", "closed": None, "expected_done": "2026-10-02T15:30:00",
    "technician_id": "T-JORDAN", "fault_event_ids": [],
    "operating_hours_at_close": None, "labor_minutes": None, "parts": [],
})

CURRENT = {   # status, zone, one-line update
    "EX-01": ("Active", "pit", "Running 5.8 hours today, no warnings"),
    "EX-03": ("In repair", "shop", "250-hour service, about 70% done. Tech: Jordan"),
    "EX-07": ("Warning", "pit", "Boom sensor warning came on twice today, 10:12 and 13:40"),
    "EX-08": ("Idle", "pit", "Parked since 12:30, no faults"),
    "EX-10": ("Active", "crush", "Loading stockpile, 6.1 hours today"),
    "DZ-02": ("Active", "pit", "Running 6.2 hours today, no warnings"),
    "DZ-06": ("Warning", "wash", "Sensor warning 20 minutes after washing"),
    "LD-04": ("Active", "crush", "Feeding crusher, 5.1 hours today"),
    "LD-05": ("Idle", "crush", "Parked since 11:40, no faults"),
    "HT-09": ("Active", "road", "Hauling, 18 km/h"),
    "HT-11": ("In repair", "shop", "Final drive leak. Tech: Maria. Expected back 15:00"),
    "HT-12": ("Active", "pit", "Loaded 41 times today"),
    "HT-14": ("Idle", "road", "Parked since 12:05, operator on break"),
}
for m in machines:
    status, zone, update = CURRENT[m["id"]]
    m["current"] = {"status": status, "zone": zone, "last_update": update,
                    "as_of": NOW.isoformat(), "operating_hours": hours_at(m["id"], NOW),
                    **point_in_zone(zone)}

# --------------------------------------------------------------------------
# Layer 2c: daily pre-shift inspections
# --------------------------------------------------------------------------
for m in machines:
    for d in daterange(START, END):
        r = row(m["id"], d)
        if not r["worked"]:
            continue
        finding = tire_findings.get((m["id"], d))
        inspections.append({
            "id": next_id("INS", inspections, 5), "machine_id": m["id"],
            "timestamp": (datetime.combine(d, datetime.min.time()) + timedelta(hours=6, minutes=15)).isoformat(),
            "inspector_id": rng.choice(OPERATORS),
            "result": "issue_found" if finding else "ok",
            "findings": [finding] if finding else [],
            "photo": f"media/{m['id']}_{d.isoformat()}_tire.jpg (placeholder)" if finding else None,
            "suspected_location_zone": "road" if finding else None,
        })

# --------------------------------------------------------------------------
# Answer key: what was planted (for testing, never shown in the app)
# --------------------------------------------------------------------------
answer_key = {
    "note": "Planted patterns. Your pattern code should rediscover these from the raw data.",
    "patterns": [
        {"name": "Boom harness chafe on model 336", "scope": "same model",
         "code": "SYN-E214", "machines": ["EX-01", "EX-03", "EX-08", "EX-07 (live today)"],
         "truth": "sensor_swap never holds on the 336 (4 tries); harness_reroute always holds (4 tries)",
         "demo": "Excavator #7 warning today; Strata should recommend checking the boom clamp first."},
        {"name": "Model 320 is different", "scope": "same model",
         "code": "SYN-E214", "machines": ["EX-10"],
         "truth": "On the 320, a sensor swap held. Shows why model-level patterns matter."},
        {"name": "Wash bay moisture", "scope": "location",
         "code": "SYN-E412", "machines": ["DZ-06", "LD-05", "DZ-02", "DZ-06 (live today)"],
         "truth": "Electrical warnings within ~30 min of washing; drying the connector holds. Only 3 cases: emerging."},
        {"name": "Haul road bend tire cuts", "scope": "location",
         "machines": ["HT-09", "HT-12", "HT-14"],
         "truth": "3 tire cuts in ~70 days, all traced to the inside of the bend (rock spill)."},
        {"name": "Cold-morning DEF warnings", "scope": "conditions",
         "code": "SYN-A330", "machines": ["haul trucks"],
         "truth": "Warning appears on mornings below about -6 C and clears after warm-up. Not a broken part."},
        {"name": "HT-11 final drive seal", "scope": "same machine",
         "code": "SYN-H520", "machines": ["HT-11"],
         "truth": "Seal replaced ~900 hours ago and held; leaking again today (wear, not a failed fix)."},
    ],
}

# --------------------------------------------------------------------------
# Write files
# --------------------------------------------------------------------------
os.makedirs(OUT, exist_ok=True)
fault_events.sort(key=lambda e: e["timestamp"])
work_orders.sort(key=lambda w: w["opened"])
interviews.sort(key=lambda i: i["timestamp"])
flat_telemetry = [r for mid in telemetry for r in telemetry[mid].values()]

files = {
    "site.json": {"name": "Prairie Ridge Quarry (fictional)", "map_canvas": {"width": 680, "height": 290},
                  "zones": ZONES, "now": NOW.isoformat()},
    "machines.json": machines,
    "technicians.json": TECHNICIANS,
    "fault_codes.json": FAULT_CODES,
    "telemetry_daily.json": flat_telemetry,
    "fault_events.json": fault_events,
    "work_orders.json": work_orders,
    "inspections.json": inspections,
    "interviews.json": interviews,
    "answer_key.json": answer_key,
}
for name, obj in files.items():
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)

bundle = {k.replace(".json", ""): v for k, v in files.items() if k != "answer_key.json"}
with open(os.path.join(OUT, "strata_bundle.json"), "w", encoding="utf-8") as fh:
    json.dump(bundle, fh, ensure_ascii=False)

with open(os.path.join(OUT, "telemetry_daily.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(flat_telemetry[0].keys()))
    w.writeheader()
    w.writerows(flat_telemetry)

print(f"Wrote data to {OUT}")
for name, obj in files.items():
    n = len(obj) if isinstance(obj, list) else "-"
    print(f"  {name:<22} {n}")
