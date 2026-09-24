"""5장 노선 설계 실습: 설계 JSON을 GTFS로 만들고 하남 시간표에 추가합니다.

이 모듈은 편도 버스 노선 한 개를 다룹니다. 구간별 통행시간은 사용자가 정하며,
도로망에서 추정하지 않습니다. 반환하는 신규 피드는 국제 GTFS 버스 코드 3을 씁니다.
"""
from __future__ import annotations

from datetime import date
import math
import re

from smartmob.data.gtfs import GTFS_TABLES, seconds_to_gtfs_time, validate_feed

DAY_COLUMNS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def _time(text):
    if not isinstance(text, str) or not re.fullmatch(r"\d{2}:[0-5]\d(?::[0-5]\d)?", text):
        raise ValueError("시각은 HH:MM 또는 HH:MM:SS로 적습니다. 자정 이후는 24시 이상으로 씁니다.")
    h, m, *s = map(int, text.split(":"))
    if h > 47:
        raise ValueError("실습 시각은 00:00부터 47:59:59까지입니다.")
    return h * 3600 + m * 60 + (s[0] if s else 0)


def _number(value, low, high, label, integer=False):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        raise ValueError(f"{label}에는 숫자를 입력합니다.")
    if not math.isfinite(value) or not low <= value <= high or (integer and value != int(value)):
        raise ValueError(f"{label}에는 {low}~{high} 범위의 {'정수' if integer else '숫자'}를 입력합니다.")
    return value


def make_route_feed(design: dict) -> dict:
    """HTML에서 저장한 설계와 같은 규칙으로 표 여섯 개를 만듭니다.

    첫 정류장에서 첫차 출발시각부터 배차간격마다 출발하는 운행을 생성합니다.
    출발 마감시각을 넘는 운행은 생성하지 않습니다.
    중간 정류장에만 정차시간을 더합니다. 첫·마지막 정류장의 도착과 출발은 같습니다.
    ``agency``에는 실제 운송사업자가 아닌 수업용 가상 기관을 기록합니다.
    """
    import pandas as pd

    if type(design.get("version")) is not int or design["version"] != 1:
        raise ValueError("노선 설계 파일의 version은 1이어야 합니다.")
    name = design.get("route_name", "")
    if not isinstance(name, str) or not name.strip() or len(name) > 60:
        raise ValueError("노선 이름은 1~60자입니다.")
    first, last = _time(design.get("first_departure")), _time(design.get("last_departure"))
    if last < first:
        raise ValueError("출발 마감시각은 첫차 출발시각보다 이르지 않아야 합니다. 자정 이후 시각은 24:00 이상으로 입력합니다.")
    headway = _number(design.get("headway_minutes"), 1, 180, "배차간격", True) * 60
    dwell = int(_number(design.get("dwell_seconds"), 0, 600, "정차시간", True))
    departures = list(range(first, last + 1, int(headway)))
    if len(departures) > 500:
        raise ValueError("이 실습에서는 운행을 500회까지 만듭니다. 출발 범위나 배차간격을 조정합니다.")
    try:
        if any(not isinstance(design.get(k), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", design[k])
               for k in ("start_date", "end_date")):
            raise ValueError("날짜 형식")
        start, end = date.fromisoformat(design["start_date"]), date.fromisoformat(design["end_date"])
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("운행 기간을 YYYY-MM-DD 형식의 날짜로 입력합니다.") from exc
    if end < start or not (2000 <= start.year <= end.year <= 2100):
        raise ValueError("운행 기간은 2000~2100년이며 종료일은 시작일과 같거나 이후여야 합니다.")
    days = design.get("weekdays")
    if not isinstance(days, list) or not days or any(type(d) is not int or not 0 <= d <= 6 for d in days):
        raise ValueError("운행 요일을 하나 이상 선택합니다.")
    if not any((start.weekday() + offset) % 7 in days for offset in range(min(7, (end-start).days+1))):
        raise ValueError("선택한 기간에 운행 요일이 없습니다.")
    stops = design.get("stops", [])
    if not isinstance(stops, list) or not 2 <= len(stops) <= 30:
        raise ValueError("정류장 방문 횟수는 한 운행당 2~30회로 설정합니다.")
    unique, offsets = {}, []
    elapsed = 0
    previous_id = None
    for i, stop in enumerate(stops):
        if not isinstance(stop, dict):
            raise ValueError("정류장 정보는 사전이어야 합니다.")
        sid, stop_name = stop.get("id"), stop.get("name")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+", sid):
            raise ValueError("정류장 식별자는 영문·숫자·밑줄·점·하이픈으로 적습니다.")
        if sid == previous_id:
            raise ValueError("같은 정류장을 바로 이어서 방문할 수 없습니다.")
        previous_id = sid
        if not isinstance(stop_name, str) or not stop_name.strip() or len(stop_name) > 100:
            raise ValueError("정류장 이름은 1~100자입니다.")
        lat = _number(stop.get("lat"), -90, 90, "위도")
        lon = _number(stop.get("lon"), -180, 180, "경도")
        row = [sid, stop_name.strip(), lat, lon]
        if sid in unique and row != unique[sid]:
            raise ValueError("같은 stop_id의 이름과 좌표가 서로 다릅니다.")
        unique[sid] = row
        travel = _number(stop.get("travel_minutes"), .5 if i else 0, 120 if i else 0, "구간 주행시간")
        elapsed += math.floor(travel * 60 + .5)
        arrival = elapsed
        if 0 < i < len(stops) - 1:
            elapsed += dwell
        offsets.append((arrival, elapsed))
    if departures[-1] + elapsed >= 48 * 3600:
        raise ValueError("이 실습에서는 마지막 도착이 48시 이전이어야 합니다.")

    rid, service, agency = "EDU_ROUTE_01", "EDU_SERVICE_01", "EDU_AGENCY"
    trips, visits = [], []
    for k, departure in enumerate(departures, 1):
        tid = f"EDU_TRIP_{k:03d}"
        trips.append([rid, service, tid, 0])
        for i, (stop, (arr, dep)) in enumerate(zip(stops, offsets)):
            visits.append([tid, seconds_to_gtfs_time(departure+arr),
                           seconds_to_gtfs_time(departure+dep), stop["id"], i+1])
    return {
        "agency": pd.DataFrame([[agency, "수업용 가상 운영기관", "https://example.org/", "Asia/Seoul"]],
                               columns=["agency_id", "agency_name", "agency_url", "agency_timezone"]),
        "stops": pd.DataFrame(unique.values(), columns=["stop_id", "stop_name", "stop_lat", "stop_lon"]),
        "routes": pd.DataFrame([[rid, agency, name.strip(), 3]],
                               columns=["route_id", "agency_id", "route_short_name", "route_type"]),
        "trips": pd.DataFrame(trips, columns=["route_id", "service_id", "trip_id", "direction_id"]),
        "stop_times": pd.DataFrame(visits, columns=["trip_id", "arrival_time", "departure_time",
                                                     "stop_id", "stop_sequence"]),
        "calendar": pd.DataFrame([[service, *(int(d in days) for d in range(7)),
                                     start.strftime("%Y%m%d"), end.strftime("%Y%m%d")]],
                                 columns=["service_id", *DAY_COLUMNS, "start_date", "end_date"]),
    }


def add_bus_route(feed: dict, addition: dict) -> dict:
    """수업에서 만든 버스 피드를 하남 실습 피드에 합칩니다. 원본은 바꾸지 않습니다.

    국제 버스 코드 3을 실습 버스 코드 0으로 명시적으로 바꿉니다.
    동일 stop_id는 좌표가 같을 때만 재사용합니다. 다른 식별자의 충돌은 거부합니다.
    날짜 선택은 RAPTOR와 같이 별도로 하지 않으므로 신규 노선 운행일에 비교합니다.
    반환값은 교재 계산용 피드이며 국제 코드로 통일한 배포용 GTFS가 아닙니다.
    """
    import pandas as pd

    validate_feed(feed)
    validate_feed(addition)
    if "calendar" not in addition or not addition["routes"].route_type.astype(int).eq(3).all():
        raise ValueError("신규 피드는 calendar와 국제 버스 코드 3을 사용해야 합니다.")
    for table, column in [("routes", "route_id"), ("trips", "trip_id"), ("calendar", "service_id")]:
        ids = addition[table][column].astype(str)
        if ids.duplicated().any() or set(ids) & set(feed[table][column].astype(str)):
            raise ValueError(f"{column}가 중복됩니다. 같은 노선을 두 번 추가했는지 확인합니다.")
    for child, key, parent in [("trips", "route_id", "routes"), ("trips", "service_id", "calendar"),
                               ("stop_times", "trip_id", "trips"), ("stop_times", "stop_id", "stops")]:
        if not set(addition[child][key].astype(str)) <= set(addition[parent][key].astype(str)):
            raise ValueError(f"{child}의 {key}가 {parent}에 없습니다.")
    existing = feed["stops"].set_index("stop_id")
    if addition["stops"].stop_id.duplicated().any():
        raise ValueError("신규 stops의 stop_id가 중복됩니다.")
    for stop in addition["stops"].itertuples():
        if stop.stop_id in existing.index:
            row = existing.loc[stop.stop_id]
            if not (math.isclose(float(stop.stop_lat), float(row.stop_lat), abs_tol=1e-7)
                    and math.isclose(float(stop.stop_lon), float(row.stop_lon), abs_tol=1e-7)):
                raise ValueError(f"{stop.stop_id}의 좌표가 기존 정류장과 다릅니다.")
    out = dict(feed)
    for name in GTFS_TABLES:
        extra = addition[name].copy()
        if name == "routes":
            extra["route_type"] = 0
        if name == "stops":
            extra = extra[~extra.stop_id.isin(existing.index)]
        if extra.empty:
            out[name] = feed[name].copy()
            continue
        for column in feed[name]:
            if column not in extra:
                extra[column] = pd.Series(index=extra.index, dtype=feed[name][column].dtype)
        out[name] = pd.concat([feed[name], extra], ignore_index=True)
    return out
