import os
import json
import time
import requests

HEADERS = {
    "User-Agent": "Zbiorkom to GTFS-RT (kasmar00@gmail.com)"
}

def _should_load_from_cache(file) -> bool:
    return os.path.exists(file) and (
        os.path.getmtime(file) > (time.time() - 15)
    )

def download_with_cache(url: str):
    cache_file = "cache/" + url[-10:]
    if _should_load_from_cache(cache_file):
        print(f"Serving from cache: {url}")
        with open(cache_file,"r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    
    print(f"Downloading from source: {url}")
    data = requests.get(url, headers = HEADERS).json()
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    
    return data