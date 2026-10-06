#!/usr/bin/env python3
"""
Build data/parcels.geojson for the Carriage Hill microsite.

Two modes:
  1. REAL (preferred): pass a Regrid export of tax map 157.-2-1 + sublots and a
     lot#->parcel mapping, and this merges the real geometry with the lot content
     below.  (Wire this up once the Regrid file + mapping arrive — see merge_regrid().)
  2. PROVISIONAL (default, no args): emits a schematic grid of the 26 lots near
     Roxbury village so the map/layout is reviewable before boundaries exist.
     These shapes are NOT surveyed — the map flags them as provisional.

Run:  python3 scripts/build_parcels.py           # provisional
      python3 scripts/build_parcels.py regrid.geojson   # real (after wiring merge)

Lot content is transcribed from the "Carriage Hill Lot 1 Pagers" doc (8 use-types).
"""
import json
import os
import sys

# Roxbury, NY 12474 — village center (provisional map focus only)
CENTER_LAT, CENTER_LON = 42.3012, -74.5615

# use_type -> display + color (categorical, tuned to the Places Capital palette)
TYPES = {
    "town":          {"label": "Town / Civic Use",            "color": "#6F7545"},
    "starter":       {"label": "Starter Homes & Density",     "color": "#B07D48"},
    "primary_sites": {"label": "Primary Home Sites",          "color": "#3F7A6B"},
    "primary":       {"label": "Primary Homes",               "color": "#4C6FA4"},
    "outdoor":       {"label": "Communal Outdoor",            "color": "#7B8A3A"},
    "btr":           {"label": "Build-to-Rent",               "color": "#9C5C8A"},
    "second_homes":  {"label": "High-End Second Homes",       "color": "#A8862E"},
    "hospitality":   {"label": "Micro-Hospitality",           "color": "#C0492F"},
}

# One entry per use-type cluster; lots[] carries per-lot numbers (+ optional perc note).
CLUSTERS = [
    {
        "type": "town", "lots": [2],
        "headline": "A civic anchor for Roxbury",
        "description": "Village-edge parcel with an old chicken barn and misc. debris. "
                       "Envisioned as communal space, a woodlot, or single/multi-family — "
                       "potentially donated to or partnered with the town.",
        "infrastructure": "Town water on recent bid; within ~350 ft of Main St sewer.",
    },
    {
        "type": "starter", "lots": [4, 5, 6, 7],
        "headline": "Starter homes & gentle density",
        "description": "Mostly open with some trees. An opportunity for smaller starter homes or "
                       "added density — or sale to adjoining owners, or combination into larger "
                       "DEP-approvable septic lots.",
        "infrastructure": "Water being run up Carriage Hill; septic/sewer, electric, wells TBD. "
                          "~1,100 ft to Main St sewer from Lot 7.",
    },
    {
        "type": "primary_sites", "lots": [17, 18],
        "headline": "Larger primary home sites",
        "description": "Mostly wooded with a partial shale quarry. Suited to a primary home — or "
                       "multi-family via the NYS CrossMod program with town water.",
        "infrastructure": "Town water main project awarded; ~700 ft to Main St sewer from Lot 18.",
    },
    {
        "type": "primary", "lots": [20, 21, 36, 37, 38, 40],
        "headline": "Entitled primary homes",
        "description": "A run of home sites to be entitled for primary residences, sized to support "
                       "septic without variances.",
        "infrastructure": "Septic/municipal sewer; connect to municipal water. Perc tests planned "
                          "on representative end lots.",
    },
    {
        "type": "outdoor", "lots": [23],
        "headline": "Communal outdoor retreat",
        "description": "Steep, wooded, and deep. A candidate for communal outdoor use — e.g. a small "
                       "camp with hike-to platforms and parking at the top.",
        "infrastructure": "Minimal; outdoor-recreation oriented.",
    },
    {
        "type": "btr", "lots": [41, 42, 43, 44, 45, 46],
        "headline": "Build-to-rent cluster",
        "description": "Wooded with a built road — a natural managed-rental cluster, potentially a "
                       "JV with Red Cottage. Three of six lots are just under an acre.",
        "infrastructure": "Septic/sewer, well, electric. ~700 ft from Crest Dr sewer stub "
                          "(~$35k/lot). Perc: good on Lot 43; none yet on Lot 41.",
    },
    {
        "type": "second_homes", "lots": [29, 30, 31, 32, 33],
        "headline": "High-end second homes",
        "description": "Wooded with a built road and great views — positioned for higher-end second "
                       "homes. All but one lot are just under an acre.",
        "infrastructure": "Septic/sewer, well, electric; road access. Perc: OK on Lot 29.",
    },
    {
        "type": "hospitality", "lots": [48],
        "headline": "Micro-hospitality destination",
        "description": "Wooded with a built road, great views, and a rock shelf — the standout site "
                       "for a small-scale hospitality destination.",
        "infrastructure": "Septic viable on the north end; well, electric; road access. "
                          "Perc: good on the north end.",
    },
]

PERC = {41: "No test yet", 43: "Passed", 29: "Passed", 48: "Passed (north end)"}


def all_lots():
    """Flatten clusters into an ordered list of per-lot dicts."""
    out = []
    for c in CLUSTERS:
        for n in c["lots"]:
            out.append({
                "lot": n,
                "use_type": c["type"],
                "use_label": TYPES[c["type"]]["label"],
                "color": TYPES[c["type"]]["color"],
                "status": "available",
                "headline": c["headline"],
                "description": c["description"],
                "infrastructure": c["infrastructure"],
                "perc": PERC.get(n, ""),
            })
    return out


def provisional_square(i, n_cols=6, size_lat=0.00055, size_lon=0.00075, gap=1.35):
    """A schematic square cell, laid out left-to-right / top-down from the center."""
    row, col = divmod(i, n_cols)
    lat0 = CENTER_LAT + 0.0016 - row * size_lat * gap
    lon0 = CENTER_LON - 0.0028 + col * size_lon * gap
    return [[
        [lon0, lat0],
        [lon0 + size_lon, lat0],
        [lon0 + size_lon, lat0 - size_lat],
        [lon0, lat0 - size_lat],
        [lon0, lat0],
    ]]


def build_provisional():
    feats = []
    for i, lot in enumerate(all_lots()):
        feats.append({
            "type": "Feature",
            "properties": {**lot, "provisional": True},
            "geometry": {"type": "Polygon", "coordinates": provisional_square(i)},
        })
    return {
        "type": "FeatureCollection",
        "metadata": {
            "provisional": True,
            "note": "Schematic lot layout near Roxbury village — NOT surveyed boundaries. "
                    "Replace with Regrid geometry for tax map 157.-2-1 + sublots.",
            "assemblage": {"tax_map": "157.-2-1", "lots": 25, "parcels": 26, "acres": 42,
                           "place": "Carriage Hill Rd, Roxbury, NY 12474"},
        },
        "features": feats,
    }


def merge_regrid(regrid_path):
    """
    TODO wire-up (needs the two inputs from Brad):
      - regrid_path: GeoJSON of tax map 157.-2-1 + sublots (real geometry)
      - a lot# <-> Regrid parcel (SBL / parcelnumb) mapping
    Strategy: load the Regrid FeatureCollection, index features by parcel id, then for
    each lot in all_lots() attach the matching geometry and emit a feature carrying the
    lot content properties (so the front-end is unchanged, just real shapes).
    """
    raise SystemExit(
        "Regrid merge not wired yet. Provide the Regrid export + lot#<->parcel mapping "
        "and implement the index/join here. Until then run with no args for provisional."
    )


def main():
    out_path = os.path.join(os.path.dirname(__file__), "..", "data", "parcels.geojson")
    if len(sys.argv) > 1:
        fc = merge_regrid(sys.argv[1])
    else:
        fc = build_provisional()
    with open(out_path, "w") as f:
        json.dump(fc, f, indent=2)
    print(f"Wrote {len(fc['features'])} lots -> {os.path.normpath(out_path)} "
          f"({'PROVISIONAL' if fc.get('metadata', {}).get('provisional') else 'REAL'})")


if __name__ == "__main__":
    main()
