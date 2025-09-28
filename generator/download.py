import os
import json
import time
from typing import Any
from typing_extensions import NamedTuple
import requests

HEADERS = {"User-Agent": "Zbiorkom to GTFS-RT (kasmar00@gmail.com)"}

Meta = NamedTuple("Meta", [("last_modified", Any)])

Data = NamedTuple("Data", [("data", Any), ("last_modified", str)])


def _should_load_from_cache(file) -> bool:
    return os.path.exists(file) and (os.path.getmtime(file) > (time.time() - 15))


def download_with_cache(url: str) -> Data:
    cache_file = "cache/" + url[-10:]
    cache_meta = cache_file + ".meta"
    if _should_load_from_cache(cache_file):
        print(f"Serving from cache: {url}")
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        with open(cache_meta, "r", encoding="utf-8") as f:
            meta = Meta(*json.load(f))
            last_modified = meta.last_modified
        return Data(data, last_modified)

    print(f"Downloading from source: {url}")
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    last_modified = response.headers["last-modified"]
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    with open(cache_meta, "w", encoding="utf-8") as f:
        json.dump(Meta(last_modified), f)

    return Data(data, last_modified)
