# Strata: synthetic job-site data

This folder creates one year of fake (but realistic) data for a fictional quarry, so the Strata demo has a memory to work with. All fault codes start with `SYN-`, and all serial numbers, people, and coordinates are made up.

## How to run it

You need Python 3 (already on most Macs; on Windows, install it from python.org). Nothing else to install.

```
python generate_data.py     # creates the data/ folder
python check_patterns.py    # finds the patterns and prints them
```

Running it again gives the exact same data every time, because the randomness uses a fixed seed. Change `SEED` at the top of `generate_data.py` for a different version.

## What's in data/

| File | Layer | What it is |
|---|---|---|
| `interviews.json` | 1. Technician interview | Each repair's voice debrief: the questions, the answers, and the structured "episode card." One is in Spanish. |
| `telemetry_daily.json` / `.csv` | 2. Cloud storage | One row per machine per day: hours, idle time, fuel, temperature, load, zone, and whether it got washed. Field names follow Cat's ISO 15143-3 telematics standard. |
| `fault_events.json` | 2. Cloud storage | Every warning code, with the machine, time, place, and conditions at that moment. |
| `work_orders.json` | 2. Cloud storage | Every repair and routine service, including the two open ones today. |
| `inspections.json` | 2. Cloud storage | Daily pre-shift checks. Three found tire cuts. |
| `machines.json` | Map | The 13 machines, each with today's status, zone, map position, and one-line update. |
| `site.json` | Map | The five job-site zones with their shapes on the map. |
| `technicians.json`, `fault_codes.json` | Reference | Who the technicians are, and what each code means. |
| `strata_bundle.json` | All | Everything above in one file, so the app loads a single file. |
| `answer_key.json` | Testing only | The patterns we planted. Never show this in the app. |

Layer 3 (patterns) isn't stored. It gets calculated from layers 1 and 2, which is what `check_patterns.py` does.

## The stories hidden in the data

1. **Boom sensor warning on model 336 excavators.** Replacing the sensor failed all 4 times. Rerouting the rubbing wire harness worked all 4 times, mostly done by Dale, who retired in August. Excavator #7 has this warning live today. This is the main demo.
2. **Model 320 is different.** The same warning on a different model was fixed by a sensor swap. This shows why "same model" matters.
3. **Wash bay moisture.** Electrical warnings right after pressure washing, 3 past cases across different machines. That's still an "emerging" pattern. Dozer #6 has it live today.
4. **Tire cuts at the haul road bend.** 3 in about 10 weeks, all from rock spilling on the inside of the curve. This is the map hotspot.
5. **Cold-morning DEF warnings.** These happen on freezing mornings and clear after warm-up. It's a weather pattern, not a broken part.
6. **Haul truck #11 final drive leak.** Fixed about 900 hours ago and the fix held. It's leaking again today from normal wear, and it's in the shop.

## Today's map (October 2, 2026, 2:00 PM)

- **Active:** EX-01, EX-10, DZ-02, LD-04, HT-09, HT-12
- **Idle:** EX-08, LD-05, HT-14
- **Warning:** EX-07 (north pit), DZ-06 (wash bay)
- **In repair:** EX-03 (service), HT-11 (final drive leak)
