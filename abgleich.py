import json
import csv
import re
import os
import sys

# --- KONFIGURATION ---
FILE_WIKIDATA = "query.csv"
FILE_OSM = "osm.json"
FILE_OUTPUT = "data.geojson"

# Vereinfachtes Polygon von Südtirol (Lat, Lon) für Point-in-Polygon Test
# Dies verhindert, dass Punkte in Österreich/Schweiz angezeigt werden, die nur knapp im Rechteck liegen.
SOUTH_TYROL_BORDER = [
    (46.5, 10.3), (46.8, 10.4), (46.86, 10.45), (46.82, 10.55), (46.86, 10.65), 
    (46.95, 10.75), (46.85, 11.0), (46.98, 11.15), (47.05, 11.2), (46.95, 11.35),
    (47.08, 11.5), (47.05, 11.8), (47.10, 12.0), (47.08, 12.2), (46.95, 12.25),
    (46.75, 12.45), (46.65, 12.4), (46.65, 12.2), (46.6, 12.0), (46.55, 11.8),
    (46.45, 11.8), (46.35, 11.6), (46.25, 11.4), (46.2, 11.2), (46.25, 11.0),
    (46.35, 10.9), (46.45, 10.7), (46.55, 10.5), (46.6, 10.4)
]

def is_inside_south_tyrol(lat, lon):
    """Ray-Casting Algorithmus für Punkt-in-Polygon Prüfung"""
    inside = False
    j = len(SOUTH_TYROL_BORDER) - 1
    for i in range(len(SOUTH_TYROL_BORDER)):
        xi, yi = SOUTH_TYROL_BORDER[i]
        xj, yj = SOUTH_TYROL_BORDER[j]
        
        intersect = ((yi > lat) != (yj > lat)) and \
            (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi)
        if intersect:
            inside = not inside
        j = i
    return inside

def main():
    print("--- START VERARBEITUNG ---")

    # 1. OSM LADEN (Mit Speicherung der OSM-ID)
    # Format: existing_ids['Q123'] = 'node/987654'
    existing_ids = {} 
    
    print(f"Lade {FILE_OSM}...")
    try:
        with open(FILE_OSM, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                el_type = element.get('type')
                el_id = element.get('id')
                osm_link_id = f"{el_type}/{el_id}"
                
                for key, value in tags.items():
                    if key.endswith("wikidata"):
                        found = re.findall(r'Q\d+', value, re.IGNORECASE)
                        for qid in found:
                            existing_ids[qid.upper()] = osm_link_id
                            
    except Exception as e:
        print(f"FEHLER OSM: {e}")
        # Wir machen weiter, damit zumindest die Wikidata Punkte generiert werden (alles rot)
        pass

    print(f"-> OSM Verknüpfungen: {len(existing_ids)}")

    # 2. WIKIDATA LADEN
    features = []
    matches = 0
    skipped_bounds = 0
    
    print(f"Lade {FILE_WIKIDATA}...")
    try:
        with open(FILE_WIKIDATA, 'r', encoding='utf-8') as f:
            # Quick & Dirty Dialekt Erkennung
            sample = f.read(2048)
            f.seek(0)
            if '\t' in sample: dialect = 'excel-tab'
            else: dialect = 'excel'
            
            reader = csv.DictReader(f, dialect=dialect)
            
            for row in reader:
                raw_qid = row.get('qid') or row.get('?qid') or ""
                qid = raw_qid.split('/')[-1].upper()
                
                try:
                    lat = float(row.get('lat') or row.get('?lat'))
                    lon = float(row.get('lon') or row.get('?lon'))
                    label = row.get('label') or row.get('?label') or qid
                except:
                    continue

                # STRIKTER FILTER: Polygon Prüfung
                # Zuerst grobe Bounding Box für Performance
                if not (46.2 <= lat <= 47.2 and 10.3 <= lon <= 12.5):
                    skipped_bounds += 1
                    continue
                
                # Dann feiner Polygon-Check
                if not is_inside_south_tyrol(lat, lon):
                    skipped_bounds += 1
                    continue

                # STATUS CHECK
                osm_ref = existing_ids.get(qid) # Ist None wenn nicht gefunden
                status = "done" if osm_ref else "missing"
                
                if status == "done":
                    matches += 1

                features.append({
                    "type": "Feature",
                    "properties": {
                        "wikidata": qid,
                        "name": label,
                        "status": status,
                        "osm_id": osm_ref # Speichert z.B. "way/12345" oder null
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    }
                })

    except Exception as e:
        print(f"FEHLER Wikidata: {e}")
        sys.exit(1)

    # 3. SPEICHERN
    with open(FILE_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)

    print("-" * 30)
    print(f"FERTIG.")
    print(f"Außerhalb Grenzen gefiltert: {skipped_bounds}")
    print(f"Status Done (Grün): {matches}")
    print(f"Status Missing (Rot): {len(features) - matches}")

if __name__ == "__main__":
    main()
