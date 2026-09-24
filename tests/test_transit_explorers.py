"""HTML에 쓰는 계산 기록이 제공 알고리즘·원본 시간표와 같은지 확인합니다."""
import json
import re

import pytest

from smartmob.data import load_gtfs, parse_gtfs_time
from smartmob.teaching.raptor import INF, TransitData, raptor, toy_feed
from smartmob.viz.transit import gtfs_explorer, gtfs_payload, raptor_payload


@pytest.mark.parametrize("departure", [28800, 29100, 30660])
def test_trace_preserves_answers_and_round_boundaries(departure):
    data = TransitData.from_gtfs(toy_feed(), max_transfer_m=300)
    plain = raptor(data, [(0, 0)], departure)
    traced = raptor(data, [(0, 0)], departure, record_steps=True)
    assert not plain.steps
    assert (traced.best, traced.rounds, traced.parent) == (
        plain.best, plain.rounds, plain.parent)
    assert traced.steps[0]["times"] == plain.rounds[0]
    for step in traced.steps:
        if step["kind"] == "end":
            assert step["times"] == plain.rounds[step["round"]]
        if step["kind"] == "board":
            assert step["ready"] == plain.rounds[step["round"] - 1][step["stop"]]
            assert step["departure"] >= step["ready"]
    # 08:00 예제는 D까지 같은 라운드 도보, E까지 다음 라운드 탑승입니다.
    if departure == 28800:
        walk = next(s for s in traced.steps if s["kind"] == "walk")
        assert walk["round"] == 1
        assert walk["times"][3] == 29400 + 110
        assert walk["times"][4] == INF
        arrived = next(s for s in traced.steps if s["kind"] == "ride" and s["stop"] == 4)
        assert arrived["round"] == 2 and arrived["arrival"] == 30300
        assert traced.steps[0]["times"][3] == INF  # 스냅샷은 나중 갱신으로 바뀌지 않습니다.


@pytest.fixture(scope="module")
def feed():
    return load_gtfs("hanam")


def test_export_retains_every_visit_for_selected_routes(feed):
    data = gtfs_payload(feed)
    raw = feed["stop_times"].set_index(["trip_id", "stop_sequence"])
    for route in data["routes"]:
        ids = set(feed["trips"].query('route_id == @route["id"]').trip_id)
        assert {t["id"] for t in route["trips"]} == ids
        assert sum(len(t["rows"]) for t in route["trips"]) == sum(raw.index.get_level_values(0).isin(ids))
        for trip in (route["trips"][0], route["trips"][-1]):
            for stop, sequence, arrival, departure in trip["rows"]:
                row = raw.loc[(trip["id"], sequence)]
                assert data["stops"][stop][0] == row.stop_id
                assert arrival == parse_gtfs_time(row.arrival_time)
                assert departure == parse_gtfs_time(row.departure_time)


def test_real_map_uses_the_same_results_and_round_limited_journeys(feed):
    payload = raptor_payload(feed, departures=[28800, 29100])
    data = TransitData.from_gtfs(feed)
    origins = data.access_stops(37.5393, 127.2148)
    target = payload["real"]["target"]
    assert data.stop_names[target] == "미사강변브라운스톤"
    for run in payload["real"]["runs"]:
        result = raptor(data, origins, run["departure"])
        assert run["rounds"] == result.rounds
        for k, path in enumerate(run["paths"]):
            legs = path["legs"]
            assert sum(leg["kind"] == "transit" for leg in legs) <= k
            if not path["summary"]["reachable"]:
                assert run["rounds"][k][target] == INF
                continue
            now = run["departure"]
            for leg in legs:
                if leg["kind"] == "transit":
                    assert leg["board_time"] >= now
                    now = leg["alight_time"]
                else:
                    now += leg["seconds"]
            assert now == run["rounds"][k][target]
            assert path["summary"]["total_min"] == round((now-run["departure"])/60, 1)


def test_html_is_self_contained_and_escapes_embedded_data(tmp_path):
    small = toy_feed()
    small["stops"].loc[0, "stop_name"] = '</script><script>alert("A")</script>'
    view = gtfs_explorer(small)
    payload = re.search(r'<script id="payload" type="application/json">(.*?)</script>', view.html)[1]
    assert "</script>" not in payload
    assert json.loads(payload)["stops"][0][1] == small["stops"].loc[0, "stop_name"]
    assert not re.search(r'<(?:script|link)[^>]+(?:src|href)="https?://', view.html)
    assert view.save(tmp_path / "nested/gtfs.html").read_text() == view.html
    assert 'srcdoc="' in view._repr_html_()


def test_builder_road_export_preserves_bends_and_excludes_walkways():
    from types import SimpleNamespace
    import pandas as pd
    from shapely.geometry import LineString
    from smartmob.viz.transit import _builder_roads

    bend = [(127.20, 37.54), (127.21, 37.55), (127.22, 37.54)]
    graph = SimpleNamespace(edges=pd.DataFrame([
        {"name": "실습로", "highway": "residential", "geometry": LineString(bend).wkb},
        {"name": "실습로", "highway": "residential", "geometry": LineString(bend[::-1]).wkb},
        {"name": "보도", "highway": "footway", "geometry": LineString([(127.2, 37.5), (127.3, 37.5)]).wkb},
        {"name": "고속도로", "highway": "motorway", "geometry": LineString([(127.2, 37.6), (127.3, 37.6)])},
    ]))
    roads = _builder_roads(graph)
    assert len(roads) == 2
    assert roads[0] == ["실습로", "residential", True, tuple(bend)]
    assert roads[1][2] is False  # 배경에는 남기되 새 정류장의 스냅 후보에서는 제외합니다.
