import json
import csv
import re
import os

# --- DATEINAMEN (Server-Pfade) ---
FILE_WIKIDATA = "query.csv"     # Wird vom Bot geladen
FILE_OSM = "osm.json"           # Wird vom Bot geladen
FILE_OUTPUT = "data.geojson"    # Das Ergebnis für die Karte

# --- GEOFENCE SÜDTIROL ---
MIN_LAT, MAX_LAT = 46.20, 47.15
MIN_LON, MAX_LON = 10.35, 12.55

def main():
    print("--- START SERVER ABGLEICH ---")
    
    # 1. OSM Einlesen
    existing_ids = set()
    if os.path.exists(FILE_OSM):
        try:
            with open(FILE_OSM, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for element in data.get('elements', []):
                    tags = element.get('tags', {})
                    for key, value in tags.items():
                        if key.endswith("wikidata"):
                            found = re.findall(r'Q\d+', value)
                            for qid in found:
                                existing_ids.add(qid)
            print(f"-> Gefunden in OSM: {len(existing_ids)}")
        except Exception as e:
            print(f"FEHLER bei OSM: {e}")
            return
    else:
        print("FEHLER: osm.json fehlt!")
        return

    # 2. Wikidata Einlesen & Abgleichen
    features = []
    
    if os.path.exists(FILE_WIKIDATA):
        try:
            with open(FILE_WIKIDATA, 'r', encoding='utf-8') as f:
                # CSV Dialekt ermitteln
                sample = f.read(1024)
                f.seek(0)
                try:
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

                    # OSM Check
                    if qid in existing_ids:
                        continue

                    features.append({
                        "type": "Feature",
                        "properties": {
                            "wikidata": qid,
                            "name": label
                        },
                        "geometry": {
                            "type": "Point",
                            "coordinates": [lon, lat]
                        }
                    })
        except Exception as e:
            print(f"FEHLER bei Wikidata: {e}")
            return
    else:
        print("FEHLER: query.csv fehlt!")
        return

    # 3. Speichern
    with open(FILE_OUTPUT, 'w', encoding='utf-8') as f:
        json.dump({"type": "FeatureCollection", "features": features}, f)

    print(f"-> FERTIG: {len(features)} Objekte in {FILE_OUTPUT} gespeichert.")

if __name__ == "__main__":
    main()
