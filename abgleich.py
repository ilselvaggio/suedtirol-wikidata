import json
import csv
import re
import os
import sys

# --- KONFIGURATION ---
FILE_WIKIDATA = "query.csv"
FILE_OSM = "osm.json"
FILE_OUTPUT = "data.geojson"

# Geofence (Rechteck): Alles außerhalb wird ignoriert
MIN_LAT, MAX_LAT = 46.20, 47.15
MIN_LON, MAX_LON = 10.35, 12.55

def main():
    print("--- START VERARBEITUNG ---")

    # 1. OSM LADEN (Mit ID-Speicherung für Links)
    # Mapping: wikidata_id -> osm_id (z.B. "node/12345")
    existing_ids = {} 
    
    print(f"Lade {FILE_OSM}...")
    try:
        with open(FILE_OSM, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for element in data.get('elements', []):
                tags = element.get('tags', {})
                el_type = element.get('type')
                el_id = element.get('id')
                # Erstelle den String für den Link (z.B. node/12345)
                osm_link_id = f"{el_type}/{el_id}"
                
                for key, value in tags.items():
                    if key.endswith("wikidata"):
                        found = re.findall(r'Q\d+', value, re.IGNORECASE)
                        for qid in found:
                            existing_ids[qid.upper()] = osm_link_id
                            
    except Exception as e:
        print(f"FEHLER OSM: {e}")
        # Wir brechen nicht ab, sondern erzeugen dann nur "missing" Punkte
        pass

    print(f"-> OSM Verknüpfungen: {len(existing_ids)}")

    # 2. WIKIDATA LADEN
    features = []
    matches = 0
    skipped_bounds = 0
    
    print(f"Lade {FILE_WIKIDATA}...")
    try:
        with open(FILE_WIKIDATA, 'r', encoding='utf-8') as f:
            # Schnelle Dialekterkennung
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

                # FILTER: Rechteck
                if not (MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON):
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
    print(f"Außerhalb Bounding-Box gefiltert: {skipped_bounds}")
    print(f"Status Done (Grün): {matches}")
    print(f"Status Missing (Rot): {len(features) - matches}")

if __name__ == "__main__":
    main()
