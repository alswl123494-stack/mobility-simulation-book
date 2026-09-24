"""탐색 재생의 기록과 접근성 계산을 독립적인 최단경로 결과와 비교합니다."""

import json
import math
import re

import networkx as nx
import pandas as pd
import pytest

from smartmob.data import load_road_graph
from smartmob.teaching.dijkstra import NoPath, astar, dijkstra
from smartmob.teaching.graph import RoadGraph
from smartmob.teaching.search import reachable_times, record_search
from smartmob.viz.search import search_map


@pytest.fixture
def tiny():
    # Parallel edges, a zero-cost cycle, a cheaper detour, and an isolated node.
    adj = {
        "A": [("B", 5.0, 0), ("B", 0.0, 1), ("T", 9.0, 2)],
        "B": [("A", 0.0, 3), ("T", 2.0, 4)],
        "T": [], "X": [],
    }
    coords = {n: (37.5, 127.2) for n in adj}
    edges = pd.DataFrame({"free_flow_speed_kmh": [36.0] * 5})
    return RoadGraph(adj, coords, edges, "free_flow_speed_kmh")


def test_cutoff_is_inclusive_and_excludes_tentative_nodes(tiny):
    assert reachable_times(tiny, "A", cutoff_s=0) == {"A": 0, "B": 0}
    assert reachable_times(tiny, "A", cutoff_s=1.99) == {"A": 0, "B": 0}
    assert reachable_times(tiny, "A", cutoff_s=2) == {"A": 0, "B": 0, "T": 2}


@pytest.mark.parametrize("algorithm", ["dijkstra", "astar"])
def test_trace_uses_cheaper_parallel_edge_and_stops_at_settlement(tiny, algorithm):
    trace = record_search(tiny, "A", "T", algorithm=algorithm)
    assert trace.path == ["A", "B", "T"]
    assert trace.path_edges == [1, 4]
    assert trace.times["T"] == 2
    assert trace.steps[0].updates[-1] == ("T", 9, 2)
    assert trace.steps[-1].updates == []
    assert len(trace.steps) == len(trace.times) == 3


def test_same_node_unreachable_and_missing_inputs(tiny):
    same = record_search(tiny, "A", "A")
    assert same.path == ["A"] and same.path_edges == [] and same.examined == 0
    missing_path = record_search(tiny, "A", "X")
    assert not missing_path.path and "X" not in missing_path.times
    with pytest.raises(NoPath):
        record_search(tiny, "missing")
    with pytest.raises(ValueError):
        record_search(tiny, "A", algorithm="astar")
    with pytest.raises(ValueError):
        record_search(tiny, "A", "T", algorithm="astar", cutoff_s=2)


@pytest.mark.parametrize("bad", [-1, math.inf, math.nan])
def test_invalid_costs_and_cutoffs_are_rejected(tiny, bad):
    with pytest.raises(ValueError):
        reachable_times(tiny, "A", cutoff_s=bad)
    tiny.adj["B"][0] = ("A", bad, 3)
    with pytest.raises(ValueError):
        record_search(tiny, "A", "T")


@pytest.fixture(scope="module")
def hanam():
    graph = load_road_graph("hanam", modes=("drive",))
    nxg = nx.DiGraph()
    nxg.add_nodes_from(graph.nodes)
    for u in graph.nodes:
        for v, seconds, _ in graph.neighbors(u):
            if not nxg.has_edge(u, v) or seconds < nxg[u][v]["weight"]:
                nxg.add_edge(u, v, weight=seconds)
    start = graph.nearest_node(37.5393, 127.2148)
    goal = graph.nearest_node(37.5606, 127.1930)
    return graph, nxg, start, goal


def test_real_trace_matches_reference_and_every_settled_cost(hanam):
    graph, nxg, start, goal = hanam
    expected = nx.single_source_dijkstra_path_length(nxg, start)
    edge_lookup = {
        edge: (u, v, cost)
        for u in graph.nodes for v, cost, edge in graph.neighbors(u)
    }
    for algorithm, search in [("dijkstra", dijkstra), ("astar", astar)]:
        trace = record_search(graph, start, goal, algorithm=algorithm)
        reference = search(graph, start, goal)
        assert trace.path == reference.nodes
        assert len(trace.steps) == reference.settled
        assert trace.times[goal] == pytest.approx(reference.duration_s)
        assert all(seconds == pytest.approx(expected[n]) for n, seconds in trace.times.items())
        for step in trace.steps:
            if step.incoming_edge is not None:
                parent, v, cost = edge_lookup[step.incoming_edge]
                assert v == step.node
                assert trace.times[parent] + cost == pytest.approx(step.seconds)


@pytest.mark.parametrize("minutes,count", [(2, 984), (5, 3987), (10, 8366)])
def test_real_reachability_matches_networkx(hanam, minutes, count):
    graph, nxg, start, _ = hanam
    times = reachable_times(graph, start, cutoff_s=minutes * 60)
    expected = nx.single_source_dijkstra_path_length(nxg, start, cutoff=minutes * 60)
    assert len(times) == count
    assert times == pytest.approx(expected)


def test_map_embeds_offline_data_and_escapes_labels(tiny, tmp_path):
    view = search_map(tiny, "A", "T", source_name='</script><script>alert("x")</script>')
    match = re.search(r'<script id="search-data" type="application/json">(.*?)</script>', view.html)
    payload = json.loads(match.group(1))
    assert payload["sourceName"].startswith("</script>")
    assert '</script><script>alert("x")</script>' not in view.html
    assert payload["traces"]["dijkstra"]["seconds"] == 2
    assert payload["traces"]["dijkstra"]["path"] == [0, 1, 2]
    assert "__SEARCH_DATA__" not in view.html and "srcdoc=" in view._repr_html_()
    assert view.save(tmp_path / "nested/map.html").read_text() == view.html
    access = search_map(tiny, "A", minutes=5)
    payload = json.loads(re.search(r'type="application/json">(.*?)</script>', access.html).group(1))
    assert payload["target"] is None
    assert set(payload["traces"]) == {"reach"}


def test_inconsistent_heuristic_is_rejected(tiny):
    tiny.coord["A"] = (30, 120)
    with pytest.raises(ValueError, match="일관성"):
        record_search(tiny, "A", "T", algorithm="astar")
