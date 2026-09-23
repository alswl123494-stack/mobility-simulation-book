"""저장소의 GTFS로 5~6장 HTML을 재생성합니다.

    .venv/bin/python tools/build_transit_explorers.py
"""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shapely.geometry import shape
from smartmob.data import load_gtfs, load_road_graph
from smartmob.data.paths import data_path
from smartmob.viz.transit import gtfs_explorer
from tools.build_ch06_raptor import main as build_raptor_page


def main():
    feed = load_gtfs("hanam")
    geo = json.loads(data_path("hanam/boundary.geojson").read_text())
    boundary = shape(geo["features"][0]["geometry"])
    path = gtfs_explorer(feed, boundary=boundary, road_graph=load_road_graph("hanam")).save(
        ROOT / "_static/ch05_gtfs.html")
    print(f"{path.relative_to(ROOT)} · {path.stat().st_size / 1e6:.2f} MB", flush=True)
    build_raptor_page()


if __name__ == "__main__":
    main()
