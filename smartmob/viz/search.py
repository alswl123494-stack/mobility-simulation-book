"""실습 도로망의 탐색 순서를 인터넷 없이 재생하는 지도.

    from smartmob.viz.search import search_map
    search_map(drive, start, goal)        # 다익스트라와 A* 비교
    search_map(drive, start, minutes=5)   # 5분 이내 도달 노드

반환값을 노트북 셀의 마지막 줄에 두면 지도가 나옵니다.
``view.save("outputs/search.html")``로 독립 HTML 파일을 저장할 수도 있습니다.
"""

from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass
from pathlib import Path

from smartmob.teaching.graph import RoadGraph, haversine_km
from smartmob.teaching.search import SearchTrace, record_search
from smartmob.viz.isochrones import isochrone_shapes


@dataclass
class SearchMap:
    html: str

    def _repr_html_(self) -> str:
        return (
            '<iframe title="도로망의 탐색과 도달 범위" width="100%" height="1550" '
            f'style="border:0" srcdoc="{html.escape(self.html, quote=True)}"></iframe>'
        )

    def save(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.html, encoding="utf-8")
        return out


def search_map(
    graph: RoadGraph,
    source: str,
    target: str | None = None,
    *,
    minutes: float = 10,
    source_name: str = "출발점",
    target_name: str = "목적지",
) -> SearchMap:
    """실제 노드·도로 형상 위에 제공 알고리즘의 실행 기록을 표시합니다.

    목적지가 있으면 경로 탐색 비교로, 없으면 도달 범위로 시작합니다.
    ``minutes``는 도달 범위 화면에서 선택할 수 있는 최대 시간(분)입니다.
    탐색은 그래프 전체에서 계산하며, 지도 확대 범위로 도로망을 자르지 않습니다.
    도달 범위 화면에서 등시선과 도달 노드 표시를 각각 켜고 끌 수 있습니다.
    """
    if not math.isfinite(minutes) or minutes <= 0:
        raise ValueError("minutes는 유한한 양수여야 합니다.")
    reach = record_search(graph, source, cutoff_s=minutes * 60)
    traces = {"reach": reach}
    if target is not None:
        traces["dijkstra"] = record_search(graph, source, target)
        traces["astar"] = record_search(graph, source, target, algorithm="astar")

    ids = list(graph.nodes)
    node_index = {node: i for i, node in enumerate(ids)}
    lat0, lon0 = graph.coord[source]
    east_scale = 111195.08 * math.cos(math.radians(lat0))

    def project(lon, lat):
        # Only drawing uses projected metres; search retains the original costs in seconds.
        return [round((lon - lon0) * east_scale, 1), round((lat0 - lat) * 111195.08, 1)]

    points = [project(graph.coord[n][1], graph.coord[n][0]) for n in ids]
    shapes, shape_index, edge_shapes = [], {}, {}
    has_geometry = "geometry" in graph.edges.columns
    if has_geometry:
        from shapely import from_wkb

    for u in ids:
        for v, _, edge in graph.neighbors(u):
            if edge in edge_shapes:
                continue
            if has_geometry:
                geometry = graph.edges.iloc[edge]["geometry"]
                if isinstance(geometry, (bytes, bytearray, memoryview)):
                    geometry = from_wkb(bytes(geometry))
                if geometry is None or geometry.geom_type != "LineString":
                    raise ValueError("도로 형상은 LineString이어야 합니다.")
                coords = [project(lon, lat) for lon, lat, *_ in geometry.coords]
            else:
                coords = [points[node_index[u]], points[node_index[v]]]
            key = tuple(tuple(p) for p in coords)
            key = min(key, key[::-1])  # 양방향 엣지의 같은 형상은 한 번만 저장합니다.
            if key not in shape_index:
                shape_index[key] = len(shapes)
                shapes.append(coords)
            edge_shapes[edge] = shape_index[key]

    def encode(trace: SearchTrace):
        return {
            "steps": [
                [node_index[s.node], s.seconds,
                 edge_shapes[s.incoming_edge] if s.incoming_edge is not None else -1,
                 [[node_index[v], cost] for v, cost, _ in s.updates]]
                for s in trace.steps
            ],
            "path": [node_index[n] for n in trace.path],
            "pathShapes": [edge_shapes[e] for e in trace.path_edges],
            "seconds": trace.times.get(target),
            "examined": trace.examined,
        }

    vmax = graph.max_speed_kmh() if target is not None else None
    levels = sorted({t for t in [120, 300, minutes * 60] if t <= minutes * 60})
    # Contours need known costs on BOTH sides of their threshold. A capped search
    # would incorrectly treat beyond-threshold vertices as unreachable.
    all_times = record_search(graph, source).times
    isochrones = isochrone_shapes(points, [all_times.get(n) for n in ids], levels)
    payload = {
        "ids": ids, "points": points, "shapes": shapes,
        "source": node_index[source], "target": node_index.get(target),
        "sourceName": source_name, "targetName": target_name,
        "minutes": minutes, "nEdges": graph.n_edges, "speedColumn": graph.speed_column,
        "traces": {name: encode(trace) for name, trace in traces.items()},
        "isochrones": isochrones,
        "h": [haversine_km(*graph.coord[n], *graph.coord[target])
              / vmax * 3600 for n in ids] if target is not None else [],
    }
    template = Path(__file__).with_name("search_map.html").read_text(encoding="utf-8")
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return SearchMap(template.replace("__SEARCH_DATA__", data.replace("<", "\\u003c")))
