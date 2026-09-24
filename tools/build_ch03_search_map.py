"""3장의 실제 도로망 지도를 실습 데이터로 다시 만듭니다.

저장소 루트에서: python tools/build_ch03_search_map.py
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from smartmob.data import load_road_graph
from smartmob.viz.search import search_map


def main():
    graph = load_road_graph("hanam", modes=("drive",))
    start = graph.nearest_node(37.5393, 127.2148)
    goal = graph.nearest_node(37.5606, 127.1930)
    view = search_map(
        graph, start, goal, minutes=10,
        source_name="하남시청", target_name="미사역",
    )
    out = view.save(ROOT / "_static/ch03_search_map.html")
    print(f"{out.relative_to(ROOT)} · {out.stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
