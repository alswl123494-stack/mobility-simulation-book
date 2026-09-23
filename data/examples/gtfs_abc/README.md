# 5장 A→B→C GTFS 예제

5장 「TXT 파일의 실제 내용 읽기」에 제시한 CSV 내용을 UTF-8 TXT 파일로 저장한 수업용 예제입니다. 기관·노선·정류장과 좌표는 모두 가상입니다.

- 노선: `L1` (1호선), A역 → B역 → C역
- 출발편: `L1-1` (08:00 출발), `L1-2` (08:30 출발)
- 운행일: `S`, 2026년 9월 23일 하루
- 각 구간 소요시간: 10분, 정차시간: 0초

`agency.txt`, `stops.txt`, `routes.txt`, `calendar.txt`, `trips.txt`, `stop_times.txt` 여섯 파일로 구성합니다. `../gtfs_abc.zip`에는 이 파일들이 하위 폴더 없이 들어 있습니다.

본문의 `calendar_dates.txt`는 운행일을 추가하는 별도 설명 예제이므로 기본 파일과 ZIP에는 포함하지 않았습니다.

파일을 수정한 뒤 ZIP을 다시 만들려면 이 폴더에서 다음 명령을 실행합니다.

```sh
zip -j ../gtfs_abc.zip agency.txt stops.txt routes.txt calendar.txt trips.txt stop_times.txt
```
