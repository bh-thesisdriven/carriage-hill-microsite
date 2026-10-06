#!/usr/bin/env python3
"""
Build data/parcels.geojson from the real Regrid Delaware County export.

The Carriage Hill assemblage = the 26 parcels in tax map 157.-2-* still showing the
seller "Giacci, Nancy S Ttee" as owner (Regrid was pulled right after the 8/28 closing,
so the roll hasn't flipped to Places Capital yet). We pull those parcels' real WKT
geometry + acreage + street and write GeoJSON for the map.

Run:  python3 scripts/build_from_regrid.py
Reads: ../Regrid Parcel Data/parcels/csvwktgz/ny_delaware.csv.gz  (in Drive, alongside project)
"""
import csv, gzip, json, os, re

HERE = os.path.dirname(__file__)
CSV_GZ = os.path.normpath(os.path.join(
    HERE, "..", "..", "Regrid Parcel Data", "parcels", "csvwktgz", "ny_delaware.csv.gz"))
OUT = os.path.normpath(os.path.join(HERE, "..", "data", "parcels.geojson"))

csv.field_size_limit(10**7)

# Use-based divisions (parcel = trailing number of tax map 157.-2-N). Crosswalk from Brad.
USE = [
    {"key": "community", "name": "Community", "color": "#6F7545",
     "lots": [1],
     "desc": "A village-edge parcel envisioned as communal or civic space for the town."},
    {"key": "homesites", "name": "Homesites", "color": "#4C6FA4",
     "lots": [43, 44, 45, 46, 12, 13, 15, 16, 23, 24, 26, 28],
     "desc": "Build-ready home sites near the village edge, ranging from under an acre up."},
    {"key": "str", "name": "Short-Term Rental Cluster", "color": "#C07A3E",
     "lots": [34, 35, 36, 37, 38, 39],
     "desc": "A wooded, road-served cluster suited to a managed short-term-rental community."},
    {"key": "outdoor", "name": "Outdoor Hospitality", "color": "#2E7D5B",
     "lots": [30, 31, 32, 33, 21, 22, 19],
     "desc": "View parcels suited to outdoor hospitality, retreats, and recreation."},
]
ADDITIONAL = {"key": "additional", "name": "Additional Parcels", "color": "#9A958C",
              "desc": "An additional parcel in the assemblage."}

# suffix -> use division (order index kept for sorting)
USE_BY_LOT = {}
for _i, _u in enumerate(USE):
    for _n in _u["lots"]:
        USE_BY_LOT[_n] = (_i, _u)

def lot_suffix(parcelnumb):
    nums = re.findall(r"\d+", parcelnumb)
    return int(nums[-1]) if nums else None

NUM = r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?'

def wkt_to_geometry(wkt):
    """POLYGON/MULTIPOLYGON WKT -> GeoJSON geometry via bracket substitution."""
    wkt = wkt.strip()
    up = wkt.upper()
    if up.startswith("MULTIPOLYGON"):
        gtype, body = "MultiPolygon", wkt[wkt.upper().index("MULTIPOLYGON") + 12:]
    elif up.startswith("POLYGON"):
        gtype, body = "Polygon", wkt[wkt.upper().index("POLYGON") + 7:]
    else:
        return None
    # turn "lon lat" pairs into [lon,lat]
    body = re.sub(r'(' + NUM + r')\s+(' + NUM + r')', r'[\1,\2]', body)
    body = body.replace("(", "[").replace(")", "]")
    try:
        coords = json.loads(body)
    except json.JSONDecodeError:
        return None
    return {"type": gtype, "coordinates": coords}

def nice_street(addr):
    a = (addr or "").title().strip()
    a = a.replace(" Hl ", " Hill ").replace(" Hl", " Hill")
    a = re.sub(r"\bRd\b", "Rd", a).replace(" Dr", " Dr")
    return a or "Carriage Hill area"

def main():
    feats, total_ac = [], 0.0
    with gzip.open(CSV_GZ, "rt", newline="") as f:
        for row in csv.DictReader(f):
            own = (row.get("owner") or "").lower()
            pn = row.get("parcelnumb") or ""
            if "giacci" not in own or not pn.startswith("157.-2-"):
                continue
            geom = wkt_to_geometry(row.get("wkt") or "")
            if not geom:
                print("WARN: no geometry for", pn); continue
            try:
                ac = round(float(row.get("gisacre") or row.get("deeded_acres") or 0), 2)
            except ValueError:
                ac = 0.0
            total_ac += ac
            street = nice_street(row.get("address"))
            suffix = lot_suffix(pn)
            order, u = USE_BY_LOT.get(suffix, (len(USE), ADDITIONAL))
            feats.append({
                "type": "Feature",
                "properties": {
                    "id": pn,
                    "label": f"Lot #{suffix}" if suffix is not None else pn,
                    "lot_no": suffix,
                    "parcelnumb": pn,
                    "group": u["key"],
                    "group_label": u["name"],
                    "color": u["color"],
                    "acreage": ac,
                    "street": street,
                    "status": "available",
                    "headline": f"{ac} acres" if ac else "",
                    "description": u["desc"],
                    "_order": order,
                },
                "geometry": geom,
            })
    feats.sort(key=lambda x: (x["properties"]["_order"], x["properties"].get("lot_no") or 0))
    unassigned = [f["properties"]["label"] for f in feats if f["properties"]["group"] == "additional"]
    if unassigned:
        print("UNASSIGNED (not in crosswalk, placed in 'Additional Parcels'):", unassigned)
    for f in feats:
        f["properties"].pop("_order", None)
    fc = {
        "type": "FeatureCollection",
        "metadata": {
            "provisional": False,
            "source": "Regrid Delaware County NY (csvwktgz), owner=Giacci 157.-2-*",
            "assemblage": {"tax_map": "157.-2", "parcels": len(feats),
                           "acres": round(total_ac, 1), "place": "Carriage Hill, Roxbury, NY 12474"},
        },
        "features": feats,
    }
    with open(OUT, "w") as f:
        json.dump(fc, f)
    print(f"Wrote {len(feats)} real parcels ({round(total_ac,1)} acres) -> {OUT}")
    div = {}
    for ft in feats:
        g = ft["properties"]["group_label"]
        div[g] = div.get(g, 0) + 1
    print("by division:", div)

if __name__ == "__main__":
    main()
