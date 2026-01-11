import json
import csv
import re
import os

# --- KONFIGURATION ---
FILE_WIKIDATA = "query.csv"
FILE_OSM = "osm.json"
FILE_OUTPUT = "data.geojson"

# Geofence Südtirol
MIN_LAT, MAX_LAT = 46.20, 47.15
MIN_LON, MAX_LON = 10.35, 12.55

def main():
    print("--- START ABGLEICH ---")
    
    # 1. OSM Einlesen
    existing_ids = set()
    try:
        print(f"Lade {FILE_OSM}...")
        with open(FILE_OSM, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                for key, value in tags.items():
                    if key.endswith("wikidata"):
                        found = re.findall(r'Q\d+', value)
                        for qid in found:
                            existing_ids.add(qid)
        print(f"-> OSM: {len(existing_ids)} Wikidata-Verknüpfungen gefunden.")
    except Exception as e:
        print(f"FEHLER OSM: {e}")
        return

    # 2. Wikidata Einlesen & Abgleichen
    features = []
    
    try:
        print(f"Lade {FILE_WIKIDATA}...")
        with open(FILE_WIKIDATA, 'r', encoding='utf-8') as f:
            # CSV Dialekt ermitteln (falls Tab oder Komma variiert)
            sample = f.read(1024)
            f.seek(0)
            sniffer = csv.Sniffer()
            try:
                dialect = sniffer.sniff(sample)
            except:
                dialect = 'excel'
            
            reader = csv.DictReader(f, dialect=dialect)
            
            for row in reader:
                # Spalten normalisieren
                qid = row.get('qid') or row.get('?qid')
                if qid: qid = qid.split('/')[-1]
                
                try:
                    lat = float(row.get('lat') or row.get('?lat'))
                    lon = float(row.get('lon') or row.get('?lon'))
                    label = row.get('label') or row.get('?label') or qid
                except:
                    continue 

                # Filter 1: Geofence
                if not (MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON):
                    continue

                # Filter 2: Status
                status = "done" if qid in existing_ids else "missing"

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
        print(f"FEHLER WIKIDATA: {e}")
        return

    # 3. Speichern
    with open(FILE_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)

    print(f"FERTIG. {len(features)} Objekte gespeichert in {FILE_OUTPUT}.")

if __name__ == "__main__":
    main()
