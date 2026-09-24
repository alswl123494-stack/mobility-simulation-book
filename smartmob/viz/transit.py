"""5~6장의 GTFS·RAPTOR 시각 실습. 파일로 여는 HTML을 만듭니다.
신규 노선의 배경지도는 온라인으로 읽고, 도로와 정류장은 HTML에 담습니다.

    gtfs_explorer(load_gtfs("hanam")).save("outputs/gtfs.html")
    raptor_explorer(load_gtfs("hanam")).save("outputs/raptor.html")

노트북에서는 반환값을 셀 마지막 줄에 두면 됩니다.
"""

from __future__ import annotations

import html
import json
import math
from dataclasses import dataclass
from pathlib import Path

from smartmob.data.gtfs import parse_gtfs_time
from smartmob.teaching.raptor import TransitData, journey, raptor, summarize, toy_feed


@dataclass
class TransitExplorer:
    html: str
    title: str

    def _repr_html_(self) -> str:
        return (f'<iframe title="{html.escape(self.title, quote=True)}" width="100%" '
                f'height="1300" style="border:0" '
                f'srcdoc="{html.escape(self.html, quote=True)}"></iframe>')

    def save(self, path: str | Path) -> Path:
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.html, encoding="utf-8")
        return out


def _finite(value):
    """JSON에서 무한대는 null로 표현합니다."""
    if isinstance(value, dict):
        return {k: _finite(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_finite(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _render(template, payload, title):
    base = Path(__file__).parent
    encoded = json.dumps(_finite(payload), ensure_ascii=False, allow_nan=False,
                         separators=(",", ":")).replace("<", "\\u003c")
    text = (base / template).read_text(encoding="utf-8")
    if "__BUILDER_PANEL__" in text:
        text = text.replace("__BUILDER_PANEL__", (base / "gtfs_builder_panel.html").read_text(encoding="utf-8"))
        text = text.replace("__BUILDER_SCRIPT__", (base / "gtfs_builder_script.html").read_text(encoding="utf-8"))
        vendor = base / "vendor/maplibre-gl"
        library = (vendor / "maplibre-gl.js").read_text(encoding="utf-8")
        library = library.split("//# sourceMappingURL=")[0].replace("</script", "<\\/script")
        license_text = (vendor / "LICENSE.txt").read_text(encoding="utf-8").replace("--", "—")
        text = text.replace("__BUILDER_MAP__", (
            "<!-- MapLibre GL JS 5.6.0\n" + license_text + "\n-->"
            + "<style>" + (vendor / "maplibre-gl.css").read_text(encoding="utf-8") + "</style>"
            + "<script>" + library + "</script>"
            + (base / "gtfs_builder_map.html").read_text(encoding="utf-8")))
    for key, value in {
        "__STYLE__": (base / "transit_style.html").read_text(encoding="utf-8"),
        "__COMMON__": (base / "transit_common.html").read_text(encoding="utf-8"),
        "__DATA__": encoded,
    }.items():
        text = text.replace(key, value)
    return TransitExplorer(text, title)


def _boundary(boundary):
    if boundary is None:
        return []
    polygons = list(boundary.geoms) if boundary.geom_type == "MultiPolygon" else [boundary]
    return [[[float(x), float(y)] for x, y in p.exterior.coords] for p in polygons]


def _builder_roads(graph):
    """실습 자동차 도로 형상을 보존하고 양방향으로 중복된 선만 합칩니다."""
    if graph is None:
        return []
    from shapely import from_wkb
    from smartmob.teaching.graph import DRIVE_HIGHWAYS

    seen, roads = set(), []
    for row in graph.edges.itertuples():
        if row.highway not in DRIVE_HIGHWAYS:
            continue
        geometry = row.geometry
        if isinstance(geometry, (bytes, bytearray, memoryview)):
            geometry = from_wkb(bytes(geometry))
        if geometry is None or geometry.geom_type != "LineString":
            continue
        coords = tuple((round(float(x), 7), round(float(y), 7))
                       for x, y, *_ in geometry.coords)
        key = min(coords, coords[::-1])
        if key in seen:
            continue
        seen.add(key)
        name = row.name if isinstance(row.name, str) else ""
        # 고속도로와 진출입로에는 이 정류장 실습의 새 점을 붙이지 않습니다.
        snap = row.highway not in {"motorway", "motorway_link", "trunk", "trunk_link"}
        roads.append([name, row.highway, snap, coords])
    return roads


def gtfs_payload(feed, *, route_ids=None, boundary=None, road_graph=None):
    """선택 노선의 모든 운행과 신규 노선 지도에 쓸 정류장·도로를 묶습니다."""
    routes = feed["routes"]
    if route_ids is None:
        # 본문 340번, 하남시청을 지나는 30-5번, 여러 패턴을 가진 5호선.
        examples = ["BR_1100_100100055", "BR_TAGO_GGB227000001", "RR_ACC1_S-1-5-1D"]
        available = set(routes.route_id.astype(str))
        route_ids = [rid for rid in examples if rid in available] or sorted(available)[:3]
    selected = routes[routes.route_id.astype(str).isin(route_ids)]
    if selected.empty:
        raise ValueError("선택한 노선이 피드에 없습니다.")
    trips = feed["trips"][feed["trips"].route_id.isin(selected.route_id)]
    st = feed["stop_times"][feed["stop_times"].trip_id.isin(trips.trip_id)].copy()
    st["stop_sequence"] = st.stop_sequence.astype(int)
    st = st.sort_values(["trip_id", "stop_sequence"])
    stops = feed["stops"][feed["stops"].stop_id.isin(st.stop_id)]
    index = {str(sid): i for i, sid in enumerate(stops.stop_id)}
    stop_rows = []
    for row in stops.itertuples():
        stop_rows.append([str(row.stop_id), str(row.stop_name), float(row.stop_lon),
                          float(row.stop_lat)])
    by_trip = {}
    for tid, group in st.groupby("trip_id", sort=False):
        by_trip[str(tid)] = [
            [index[str(r.stop_id)], int(r.stop_sequence), parse_gtfs_time(r.arrival_time),
             parse_gtfs_time(r.departure_time)] for r in group.itertuples()
        ]
    route_rows = []
    for route in selected.itertuples():
        subset = trips[trips.route_id == route.route_id]
        patterns = {}
        records = []
        for trip in subset.itertuples():
            rows = by_trip.get(str(trip.trip_id), [])
            if not rows:
                continue
            key = tuple(r[0] for r in rows)
            pattern = patterns.setdefault(key, len(patterns))
            records.append(dict(id=str(trip.trip_id), service=str(trip.service_id),
                                pattern=pattern, rows=rows))
        records.sort(key=lambda t: (t["rows"][0][3], t["id"]))
        route_rows.append(dict(id=str(route.route_id), name=str(route.route_short_name),
                               type=int(route.route_type), trips=records,
                               patterns=len(patterns)))
    builder_stops = [[str(r.stop_id), str(r.stop_name), float(r.stop_lon), float(r.stop_lat)]
                     for r in feed["stops"].itertuples()]
    return dict(stops=stop_rows, routes=route_rows, boundary=_boundary(boundary),
                builderStops=builder_stops, builderRoads=_builder_roads(road_graph),
                calendar=feed.get("calendar").astype(str).to_dict("records")
                if "calendar" in feed else [])


def gtfs_explorer(feed, *, route_ids=None, boundary=None, road_graph=None) -> TransitExplorer:
    """GTFS를 읽고 만듭니다. road_graph를 주면 신설 정류장의 좌표를 도로에 맞춥니다.

    boundary는 위경도 Shapely 경계입니다. 배경지도는 인터넷으로 읽으며,
    정류장·도로·스냅과 GTFS 생성은 HTML에 포함된 자료로 작동합니다.
    """
    return _render("gtfs_explorer.html", gtfs_payload(feed, route_ids=route_ids,
                   boundary=boundary, road_graph=road_graph), "GTFS의 구조와 버스 노선 설계")


def raptor_payload(feed, *, boundary=None, departures=(25200, 28800, 29100, 30600, 10800)):
    """교재 예제의 단계 기록과 하남 실습의 라운드별 실제 계산값을 묶습니다.

    날짜 필터, 승하차 제한, 실시간 지연은 이 장의 제공 RAPTOR와 같이 생략합니다.
    """
    toy = TransitData.from_gtfs(toy_feed(), max_transfer_m=300)
    examples = []
    for departure in (28800, 29100, 30660):
        res = raptor(toy, [(toy.index_of["A"], 0)], departure, record_steps=True)
        examples.append(dict(departure=departure, steps=res.steps, rounds=res.rounds))
    toy_patterns = [dict(name=p.name, stops=p.stops, departures=p.departures,
                         arrivals=p.arrivals) for p in toy.patterns]
    data = TransitData.from_gtfs(feed)
    origins = data.access_stops(37.5393, 127.2148)
    target = data.nearest_stop(37.5606, 127.1930)
    runs = []
    for departure in departures:
        res = raptor(data, origins, int(departure))
        paths = []
        # 각 탑승 제한의 경로도 제공 알고리즘으로 직접 복원합니다.
        for k in range(len(res.rounds)):
            limited = raptor(data, origins, int(departure), max_rounds=k)
            legs = journey(data, limited, target)
            paths.append(dict(legs=legs, summary=summarize(data, legs, int(departure))))
        runs.append(dict(departure=int(departure), rounds=res.rounds, paths=paths))
    return dict(toy=dict(stops=toy.stop_ids, patterns=toy_patterns,
                         walks=[(i, j, s) for i, row in enumerate(toy.transfers)
                                for j, s in row if i < j], runs=examples),
                real=dict(stops=list(zip(data.stop_ids, data.stop_names,
                                         data.stop_lons, data.stop_lats)),
                          patterns=[p.stops for p in data.patterns], runs=runs,
                          target=target, origin=[127.2148, 37.5393],
                          counts=data.describe(), boundary=_boundary(boundary)))


def raptor_explorer(feed, *, boundary=None, view="toy") -> TransitExplorer:
    """작은 시간표와 하남시청 출발 라우팅을 비교합니다. view='hanam'은 지도부터 엽니다."""
    if view not in {"toy", "hanam"}:
        raise ValueError("view는 'toy' 또는 'hanam'입니다.")
    payload = raptor_payload(feed, boundary=boundary)
    payload["view"] = view
    return _render("raptor_explorer.html", payload, "RAPTOR의 라운드와 도달 범위")
