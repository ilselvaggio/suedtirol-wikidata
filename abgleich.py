import json
import csv
import re
import os

# Dateien
FILE_WIKIDATA = "query.csv"
FILE_OSM = "osm.json"
FILE_OUTPUT = "data.geojson"

# Geofence Südtirol
MIN_LAT, MAX_LAT = 46.20, 47.15
MIN_LON, MAX_LON = 10.35, 12.55

def main():
    print("--- START ABGLEICH ---")
    
    # 1. OSM laden
    existing_ids = set()
    if os.path.exists(FILE_OSM):
        try:
            with open(FILE_OSM, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for element in data.get('elements', []):
                    tags = element.get('tags', {})
                    for key, value in tags.items():
                        if "wikidata" in key: # Fangt wikidata, brand:wikidata etc.
                            found = re.findall(r'Q\d+', value)
                            for qid in found:
                                existing_ids.add(qid)
            print(f"OSM Daten geladen: {len(existing_ids)} Verknüpfungen gefunden.")
        except Exception as e:
            print(f"FEHLER OSM JSON: {e}")
    else:
        print("WARNUNG: osm.json fehlt! Alles wird als 'fehlend' markiert.")

    # 2. Wikidata verarbeiten
    features = []
    
    if os.path.exists(FILE_WIKIDATA):
        with open(FILE_WIKIDATA, 'r', encoding='utf-8') as f:
            # CSV Format erkennen
            try:
                sample = f.read(1024)
                f.seek(0)
                dialect = csv.Sniffer().sniff(sample)
            except:
                dialect = 'excel'
            
            reader = csv.DictReader(f, dialect=dialect)
            
            for row in reader:
                qid = row.get('qid') or row.get('?qid')
                if qid: qid = qid.split('/')[-1]
                
                try:
                    lat = float(row.get('lat') or row.get('?lat'))
                    lon = float(row.get('lon') or row.get('?lon'))
                    label = row.get('label') or row.get('?label') or qid
                except:
                    continue 

                # Geofence Check
                if not (MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON):
                    continue

                # STATUS BESTIMMEN
                if qid in existing_ids:
                    status = "done"
                else:
                    status = "missing"

                features.append({
                    "type": "Feature",
                    "properties": {
                        "wikidata": qid,
                        "name": label,
                        "status": status  # Wichtig für die Einfärbung
                    },
                    "geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    }
                })
    
    # 3. Speichern
    with open(FILE_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)
    
    print(f"Fertig. {len(features)} Objekte gespeichert.")

if __name__ == "__main__":
    main()
