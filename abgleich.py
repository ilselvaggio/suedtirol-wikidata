import json
import csv
import re
import os
import sys

# --- CONFIG ---
FILE_WIKIDATA = "query.csv"
FILE_OSM = "osm.json"
FILE_OUTPUT = "data.geojson"
MIN_LAT, MAX_LAT = 46.20, 47.15
MIN_LON, MAX_LON = 10.35, 12.55

def main():
    print("--- DIAGNOSE START ---")

    # CHECK 1: Existieren die Dateien und haben sie Inhalt?
    for fname in [FILE_OSM, FILE_WIKIDATA]:
        if not os.path.exists(fname):
            print(f"FATAL: {fname} fehlt!")
            sys.exit(1)
        size = os.path.getsize(fname)
        print(f"Datei {fname}: {size} Bytes")
        if size < 100:
            print(f"WARNUNG: {fname} ist verdächtig klein. Inhalt:")
            with open(fname, 'r') as f: print(f.read())

    # 2. OSM LADEN
    existing_ids = set()
    print(f"\nLade {FILE_OSM}...")
    try:
        with open(FILE_OSM, 'r', encoding='utf-8') as f:
            # Testen ob valid JSON
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print("FATAL: osm.json ist kein gültiges JSON! Wahrscheinlich Overpass-Timeout oder Fehler 500.")
                sys.exit(1)

            elements = data.get('elements', [])
            print(f"OSM Elemente roh: {len(elements)}")
            
            for element in elements:
                tags = element.get('tags', {})
                for key, value in tags.items():
                    # Regex sucht nach Q-Nummern in ALLEN Tags, die auf wikidata enden
                    if key.endswith("wikidata"):
                        # Sucht Q12345 (case insensitive falls jemand q1234 schreibt)
                        found = re.findall(r'Q\d+', value, re.IGNORECASE)
                        for qid in found:
                            existing_ids.add(qid.upper()) # Normalisieren auf Q...
                            
    except Exception as e:
        print(f"FEHLER beim Lesen von OSM: {e}")
        sys.exit(1)

    print(f"-> Gefundene Unique Wikidata-IDs in OSM: {len(existing_ids)}")
    if len(existing_ids) > 0:
        print(f"Beispiel IDs aus OSM: {list(existing_ids)[:5]}")
    else:
        print("ACHTUNG: 0 IDs in OSM gefunden. Daher wird alles rot sein.")

    # 3. WIKIDATA LADEN & ABGLEICH
    features = []
    matches = 0
    print(f"\nLade {FILE_WIKIDATA}...")
    
    try:
        with open(FILE_WIKIDATA, 'r', encoding='utf-8') as f:
            # Fallback für Dialekt
            content = f.read()
            f.seek(0)
            if '\t' in content: dialect = 'excel-tab'
            else: dialect = 'excel'
            
            reader = csv.DictReader(f)
            
            for row in reader:
                # Flexible Spaltennamen
                raw_qid = row.get('qid') or row.get('?qid') or ""
                qid = raw_qid.split('/')[-1].upper() # Clean URL -> QID
                
                try:
                    lat = float(row.get('lat') or row.get('?lat'))
                    lon = float(row.get('lon') or row.get('?lon'))
                    label = row.get('label') or row.get('?label') or qid
                except:
                    continue

                # Geofence
                if not (MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON):
                    continue

                # STATUS CHECK
                if qid in existing_ids:
                    status = "done"
                    matches += 1
                else:
                    status = "missing"

                features.append({
                    "type": "Feature",
                    "properties": {
                        "wikidata": qid,
                        "name": label,
                        "status": status
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    }
                })

    except Exception as e:
        print(f"FEHLER Wikidata: {e}")
        sys.exit(1)

    # 4. Speichern
    with open(FILE_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)

    print("-" * 30)
    print(f"FERTIG. Matches (Grün): {matches}")
    print(f"Fehlend (Rot): {len(features) - matches}")
    print(f"Datei gespeichert: {FILE_OUTPUT}")

if __name__ == "__main__":
    main()
