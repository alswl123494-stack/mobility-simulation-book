"""직접 만든 시간표의 시각·식별자·운행일과 하남 피드 결합을 검사합니다."""
from copy import deepcopy

import pandas as pd
import pytest

from smartmob.data import load_gtfs
from smartmob.teaching.gtfs_builder import add_bus_route, make_route_feed
from smartmob.teaching.raptor import TransitData, raptor


@pytest.fixture
def design():
    return dict(version=1, route_name='실습, "01"', first_departure="07:00",
                last_departure="09:00", headway_minutes=20, dwell_seconds=30,
                start_date="2026-01-01", end_date="2026-12-31", weekdays=[0, 1, 2, 3, 4],
                stops=[dict(id="A", name="가", lat=37.54, lon=127.21, travel_minutes=0),
                       dict(id="B", name="나", lat=37.56, lon=127.19, travel_minutes=6),
                       dict(id="C", name="다", lat=37.58, lon=127.18, travel_minutes=3)])


def test_rows_ids_and_dwell(design):
    feed = make_route_feed(design)
    assert {name: len(table) for name, table in feed.items()} == {
        "agency": 1, "stops": 3, "routes": 1, "trips": 7, "stop_times": 21, "calendar": 1}
    first = feed["stop_times"].iloc[:3]
    assert list(first.arrival_time) == ["07:00:00", "07:06:00", "07:09:30"]
    assert list(first.departure_time) == ["07:00:00", "07:06:30", "07:09:30"]
    assert feed["routes"].route_type.iloc[0] == 3
    assert set(feed["trips"].trip_id) == set(feed["stop_times"].trip_id)
    assert set(feed["trips"].route_id) == set(feed["routes"].route_id)
    assert set(feed["trips"].service_id) == set(feed["calendar"].service_id)
    assert set(feed["routes"].agency_id) == set(feed["agency"].agency_id)


def test_headway_changes_wait_but_not_stops_or_running_time(design):
    results = []
    for minutes, count in [(20, 7), (10, 13)]:
        design["headway_minutes"] = minutes
        feed = make_route_feed(design)
        assert len(feed["trips"]) == count
        assert len(feed["stop_times"]) == count * 3
        data = TransitData.from_gtfs(feed)
        result = raptor(data, [(data.index_of["A"], 0)], 8*3600+180)
        results.append(result.best[data.index_of["C"]])
    assert results == [8*3600+29*60+30, 8*3600+19*60+30]


def test_midnight_and_non_aligned_departure_limit(design):
    design.update(first_departure="23:50", last_departure="24:31")
    feed = make_route_feed(design)
    assert list(feed["stop_times"].groupby("trip_id").first().departure_time) == [
        "23:50:00", "24:10:00", "24:30:00"]
    assert feed["stop_times"].arrival_time.iloc[-1] == "24:39:30"


def test_repeated_stop_has_one_stop_row_but_multiple_visits(design):
    design["stops"].append({**design["stops"][0], "travel_minutes": 8})
    feed = make_route_feed(design)
    assert len(feed["stops"]) == 3 and len(feed["stop_times"]) == 7*4
    assert list(feed["stop_times"].iloc[:4].stop_sequence) == [1, 2, 3, 4]


@pytest.mark.parametrize("changes", [
    {"headway_minutes": 0}, {"headway_minutes": 2.5}, {"dwell_seconds": -1},
    {"first_departure": "08:60"}, {"last_departure": "06:00"},
    {"first_departure": "00:00", "last_departure": "24:00", "headway_minutes": 1},
    {"first_departure": "47:55", "last_departure": "47:59"},
    {"weekdays": []}, {"weekdays": [True]}, {"route_name": "  "},
    {"start_date": "2026-02-30"}, {"end_date": "2025-01-01"},
    {"start_date": "2026-09-27", "end_date": "2026-09-27"},
    {"stops": []},
])
def test_invalid_inputs_are_rejected(design, changes):
    design.update(changes)
    with pytest.raises(ValueError):
        make_route_feed(design)


def test_invalid_stops_are_rejected(design):
    for change in [dict(lat=float("nan")), dict(lon=181), dict(travel_minutes=-1), dict(name="")]:
        edited = deepcopy(design)
        edited["stops"][1].update(change)
        with pytest.raises(ValueError):
            make_route_feed(edited)


def test_adding_new_route_reuses_stops_and_preserves_originals(design):
    base = load_gtfs("hanam")
    ids = ["BS_TAGO_GGB227000034", "BS_TAGO_GGB227000506", "BS_TAGO_GGB227000658"]
    stops = base["stops"].set_index("stop_id")
    for stop, sid in zip(design["stops"], ids):
        row = stops.loc[sid]
        stop.update(id=sid, name=row.stop_name, lat=float(row.stop_lat), lon=float(row.stop_lon))
    design["headway_minutes"] = 10
    addition = make_route_feed(design)
    original = {name: df.copy(deep=True) for name, df in base.items()}
    merged = add_bus_route(base, addition)
    assert len(merged["stops"]) == len(base["stops"])
    assert len(merged["routes"]) == len(base["routes"]) + 1
    assert len(merged["trips"]) == len(base["trips"]) + 13
    assert merged["routes"].route_type.iloc[-1] == 0
    assert addition["routes"].route_type.iloc[0] == 3
    for name in base:
        pd.testing.assert_frame_equal(base[name], original[name])
    data = TransitData.from_gtfs(merged)
    result = raptor(data, data.access_stops(37.5393, 127.2148), 28800)
    assert result.best[data.index_of[ids[1]]] == 8*3600+16*60
    with pytest.raises(ValueError, match="중복"):
        add_bus_route(merged, addition)
    addition["stops"].loc[0, "stop_lat"] += .01
    with pytest.raises(ValueError, match="좌표"):
        add_bus_route(base, addition)


def test_broken_foreign_keys_are_rejected(design):
    base = load_gtfs("hanam")
    extra = make_route_feed(design)
    extra["stop_times"].loc[0, "trip_id"] = "missing"
    with pytest.raises(ValueError, match="trip_id"):
        add_bus_route(base, extra)
