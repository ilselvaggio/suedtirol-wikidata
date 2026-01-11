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

    # CHECK 1: Existieren die Dateien?
    for fname in [FILE_OSM, FILE_WIKIDATA]:
        if not os.path.exists(fname):
            print(f"FATAL: {fname} fehlt!")
            sys.exit(1)
        size = os.path.getsize(fname)
        print(f"Datei {fname}: {size} Bytes")

    # 2. OSM LADEN
    existing_ids = set()
    print(f"\nLade {FILE_OSM}...")
    try:
        with open(FILE_OSM, 'r', encoding='utf-8') as f:
            content = f.read()
            # Versuch JSON zu parsen
            try:
                data = json.loads(content)
            except json.JSONDecodeError as e:
                print("FATAL: osm.json ist kein gültiges JSON!")
                print("--- DATEI INHALT (Start) ---")
                print(content[:2000]) # Zeige die Fehlermeldung
                print("--- DATEI INHALT (Ende) ---")
                sys.exit(1)

            elements = data.get('elements', [])
            print(f"OSM Elemente roh: {len(elements)}")
            
            for element in elements:
                tags = element.get('tags', {})
                for key, value in tags.items():
                    if key.endswith("wikidata"):
                        found = re.findall(r'Q\d+', value, re.IGNORECASE)
                        for qid in found:
                            existing_ids.add(qid.upper())
                            
    except Exception as e:
        print(f"FEHLER beim Lesen von OSM: {e}")
        sys.exit(1)

    print(f"-> Gefundene Unique Wikidata-IDs in OSM: {len(existing_ids)}")

    # 3. WIKIDATA LADEN & ABGLEICH
    features = []
    matches = 0
    print(f"\nLade {FILE_WIKIDATA}...")
    
    try:
        with open(FILE_WIKIDATA, 'r', encoding='utf-8') as f:
            sniffer = csv.Sniffer()
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = sniffer.sniff(sample)
            except:
                dialect = 'excel'
            
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

                if not (MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON):
                    continue

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
    
    # Check ob wirklich was passiert ist
    if matches == 0 and len(existing_ids) > 0:
        print("WARNUNG: 0 Matches obwohl OSM Daten da sind. Prüfe QID Formate (Q123 vs q123)!")

if __name__ == "__main__":
    main()
