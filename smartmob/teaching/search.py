"""3장 지도 실습: 확정 순서를 기록하고 시간 제한 안의 도달 노드를 구합니다.

    times = reachable_times(drive, start, cutoff_s=5 * 60)

학생이 작성하는 함수는 ``labs/ch03_dijkstra.py``에 있습니다. 이 모듈은
그와 같은 확정·완화 규칙에 지도 재생용 기록을 붙인 제공 코드입니다.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

from smartmob.teaching.dijkstra import NoPath
from smartmob.teaching.graph import RoadGraph, haversine_km


@dataclass
class SearchStep:
    node: str
    seconds: float
    incoming_edge: int | None
    updates: list[tuple[str, float, int]]


@dataclass
class SearchTrace:
    steps: list[SearchStep]
    times: dict[str, float]  # 확정된 값만 담습니다.
    path: list[str]
    path_edges: list[int]
    examined: int


def record_search(
    graph: RoadGraph,
    source: str,
    target: str | None = None,
    *,
    algorithm: str = "dijkstra",
    cutoff_s: float | None = None,
) -> SearchTrace:
    """노드 하나의 확정과 이웃 완화를 한 단계로 기록합니다.

    목적지가 없으면 도달 가능한 노드를 계속 확정합니다. ``cutoff_s``가
    있으면 그 시간 이하인 노드까지만 확정합니다(다익스트라에만 사용).
    목적지에 갈 수 없으면 ``path``가 비며, 조사한 순서는 그대로 남습니다.
    """
    if source not in graph.adj or (target is not None and target not in graph.adj):
        raise NoPath("출발·도착 노드가 그래프에 없습니다.")
    if algorithm not in {"dijkstra", "astar"}:
        raise ValueError("algorithm은 'dijkstra' 또는 'astar'입니다.")
    if cutoff_s is not None and (not math.isfinite(cutoff_s) or cutoff_s < 0):
        raise ValueError("cutoff_s는 유한한 0 이상의 초입니다.")
    if algorithm == "astar" and (target is None or cutoff_s is not None):
        raise ValueError("A*에는 목적지를 지정하고 시간 제한은 사용하지 않습니다.")
    for u in graph.nodes:
        for _, seconds, _ in graph.neighbors(u):
            if not math.isfinite(seconds) or seconds < 0:
                raise ValueError("엣지 통행시간은 유한한 0 이상의 값이어야 합니다.")

    h = dict.fromkeys(graph.nodes, 0.0)
    if algorithm == "astar":
        vmax = graph.max_speed_kmh()
        if not math.isfinite(vmax) or vmax <= 0:
            raise ValueError("도로망의 최고 속도가 유효하지 않습니다.")
        h = {
            n: haversine_km(*graph.coord[n], *graph.coord[target]) / vmax * 3600
            for n in graph.nodes
        }
        if any(
            h[u] > seconds + h[v] + 1e-7
            for u in graph.nodes
            for v, seconds, _ in graph.neighbors(u)
        ):
            raise ValueError("직선거리 휴리스틱이 일관성을 만족하지 않는 도로망입니다.")

    dist = {source: 0.0}
    prev: dict[str, tuple[str, int]] = {}
    times: dict[str, float] = {}
    heap = [(h[source], 0.0, source)]
    steps = []
    examined = 0

    while heap:
        _, seconds, u = heapq.heappop(heap)
        if u in times:
            continue
        # 다익스트라는 최소 잠정 시간부터 꺼내므로 이후 후보도 제한을 넘습니다.
        if cutoff_s is not None and seconds > cutoff_s:
            break
        times[u] = seconds
        step = SearchStep(u, seconds, prev[u][1] if u in prev else None, [])
        steps.append(step)
        if u == target:
            break
        for v, weight, edge in graph.neighbors(u):
            examined += 1
            if v in times:
                continue
            candidate = seconds + weight
            if candidate < dist.get(v, math.inf):
                dist[v] = candidate
                prev[v] = (u, edge)
                heapq.heappush(heap, (candidate + h[v], candidate, v))
                step.updates.append((v, candidate, edge))

    path, path_edges = [], []
    if target is not None and target in times:
        path = [target]
        while path[-1] != source:
            parent, edge = prev[path[-1]]
            path.append(parent)
            path_edges.append(edge)
        path.reverse()
        path_edges.reverse()
    return SearchTrace(steps, times, path, path_edges, examined)


def reachable_times(graph: RoadGraph, source: str, *, cutoff_s: float) -> dict[str, float]:
    """출발 노드에서 cutoff_s 초 이내에 도달하는 노드와 최단시간을 반환합니다.

    출발점 자체(0초)도 포함합니다. 도로의 방향과 현재의 고정 통행시간을 씁니다.
    """
    return record_search(graph, source, cutoff_s=cutoff_s).times
