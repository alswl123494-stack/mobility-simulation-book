---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.16.4
kernelspec:
  display_name: Python 3
  language: python
  name: python3
---

# 0장 환경 준비

실습에는 파이썬 환경, 예제 데이터, 시뮬레이션 엔진이 필요합니다. 셋 다 저장소 안에 들어 있어서 별도의 서버를 준비하지 않아도 됩니다. 이 장에서는 패키지 설치와 데이터 경로를 확인하고, 하남시 택시 시뮬레이션을 한 번 돌려 결과를 읽습니다.

운영체제와 라이브러리 버전에 따라 설치 로그와 실행 시간이 다를 수 있습니다. 각 절에 적힌 확인 코드와 데이터 규모, 테스트 결과를 기준으로 환경을 점검합니다.

## 학습 목표

- 실습 환경을 설치하고 `smartmob` 이 불러와지는지 확인합니다
- 하남시 도로망을 읽어 노드와 엣지 수를 셉니다
- 시뮬레이션 엔진이 서버 없이 노트북 안에서 도는 것을 확인합니다
- 시뮬레이션을 한 번 돌리고 서비스율과 평균 대기시간을 읽습니다

## 0.1 설치

파이썬 3.11을 씁니다. 먼저 저장소를 받습니다.

```bash
git clone https://github.com/jihoyeo/mobility-simulation-book.git
cd mobility-simulation-book
```

다음으로 이 책 전용 가상환경을 만듭니다. 가상환경은 이 수업에서 쓰는 패키지를 컴퓨터의 다른 파이썬 환경과 분리해 둡니다. 다른 수업이나 연구에서 쓰던 패키지 버전과 충돌하지 않고, 정리하고 싶으면 `.venv` 디렉터리만 삭제하면 됩니다.

```bash
python -m venv .venv
source .venv/bin/activate          # 윈도우 파워셸: .venv\Scripts\Activate.ps1
```

프롬프트 맨 앞에 `(.venv)` 가 나타나면 활성화된 것입니다. 터미널을 새로 열 때마다 활성화 명령을 다시 실행해야 합니다. 아나콘다를 이미 쓰고 있다면 `conda create -n smartmob python=3.11` 로 만든 환경을 대신 써도 됩니다.

가상환경을 활성화한 상태에서 의존성을 설치합니다.

```bash
pip install -r requirements.txt
```

`requirements.txt` 는 버전을 전부 고정해 두었습니다. 같은 버전을 쓰면 같은 그림이 나옵니다. 마지막 줄의 `-e .` 는 저장소 안의 `smartmob` 패키지를 함께 설치하라는 뜻입니다. 그래서 어느 디렉터리에서 파이썬을 켜도 `import smartmob` 이 됩니다. 9장에서 쓰는 `scikit-learn` 과 `LightGBM`, 실습 노트북을 여는 `JupyterLab` 도 여기에 포함되어 있습니다.

설치가 끝나면 한 줄로 확인합니다. 오류 없이 버전 번호가 찍히면 됩니다.

```bash
python -c "import smartmob; print(smartmob.__version__)"
```

2장에서 OSM 원본을 직접 내려받아 도로망을 만들어 보려면 `osmnx` 가 더 필요합니다. 본문은 이미 만들어 둔 파일을 쓰기 때문에 설치하지 않아도 됩니다.

```bash
pip install -r requirements-heavy.txt
```

12장의 웹 뷰어는 파이썬이 아니라 Node 로 돕니다. 이 책에서 유일한 예외입니다. 12주차에 가서 설치해도 됩니다. [nodejs.org](https://nodejs.org) 에서 LTS 판을 받습니다. 20.19 이상이면 됩니다.

```{note}
구글 코랩에서 읽는다면 각 장 위쪽의 Colab 배지를 누르고, 첫 셀에서 `smartmob.colab.bootstrap()` 을 실행합니다. 한글 폰트를 깔고 패키지를 설치합니다.
```

```{note}
설치에 실패하면 실행한 명령, 오류 전문, 운영체제, 파이썬 버전을 함께 기록합니다. 설치 확인 기준은 다음 절의 `import smartmob`이 오류 없이 실행되는지입니다.
```

```{admonition} AI 에게 물어보기 — 설치
:class: tip

설치는 컴퓨터마다 다른 자리에서 막힙니다. 명령의 뜻을 모르겠거나 오류가 나면 그대로 물어봅니다.

> `pip install -r requirements.txt` 가 무슨 일을 하는 명령인지 한 줄씩 설명해 줘.

> 윈도우 파워셸에서 `.venv\Scripts\Activate.ps1` 을 실행했더니 실행 정책 때문에 막혔어. 어떻게 해야 하는지 알려 줘.

> 아래 오류가 났어. 윈도우 11 이고 파이썬은 3.11 이야. (오류 메시지를 통째로 붙여넣기)

클로드 코드나 커서 같은 AI 코딩 도구를 쓴다면 설치를 통째로 맡겨도 됩니다.

> 이 저장소를 받아서 파이썬 3.11 가상환경을 만들고 `requirements.txt` 를 설치해 줘. 끝나면 `import smartmob` 이 되는지 확인해 줘.

맡기더라도 마지막 확인은 직접 합니다. `import smartmob` 이 오류 없이 지나가면 다음 절로 넘어갑니다.
```

## 0.2 데이터가 있는지 확인하기

실습 도시는 **하남시**입니다. 서울과 붙어 있으면서 노트북에서 다루기 좋은 크기라 골랐습니다. 도로망과 대중교통 시간표가 저장소에 이미 들어 있습니다.

```{code-cell} python
from smartmob.data import data_path

for name in ["road_graph_nodes.parquet", "road_graph_edges.parquet", "demand.csv"]:
    p = data_path(f"hanam/{name}")
    print(f"{name:28s} {p.stat().st_size / 1e6:6.2f} MB")
```

도로망을 읽어 봅니다. `modes=("drive",)` 는 자동차가 다닐 수 있는 도로만 남기라는 뜻입니다. 왜 이 인자가 필요한지는 2장에서 다룹니다.

```{code-cell} python
from smartmob.data import load_road_graph

G = load_road_graph("hanam", modes=("drive",))
G
```

노드가 12,566개, 엣지가 28,589개입니다. 하남시 전체 도로망치고는 적어 보이지만, 교차로와 막다른 길만 노드로 잡고 그 사이 직선 구간은 엣지 하나로 묶은 결과입니다.

```{note}
`FileNotFoundError`가 나면 노트북의 현재 작업 디렉터리와 `data/hanam/` 경로를 먼저 확인합니다.
```

## 0.3 시뮬레이션 엔진 준비하기

시뮬레이션을 실제로 계산하는 부분을 엔진이라고 부릅니다. `smartmob` 은 엔진 둘 중 하나를 골라 씁니다.

**내장 엔진**은 `smartmob` 안에 파이썬으로 들어 있습니다. 설치 말고는 준비할 것이 없고, 노트북 안에서 그 자리에서 계산합니다. 승객 1,000명·차량 80대 규모가 1초 안에 끝납니다. **이 책의 기본값입니다.** 0장부터 9장까지는 이 엔진만으로 끝까지 진행합니다.

**DTUMOS** 는 Rust 로 짜인 별도 프로그램이고 Docker 컨테이너로 돕니다. 대중교통 경로 질의(7장)와 대규모 실험(12장)에만 필요합니다. 필요해지는 시점에 [부록 B](appendix_b_ops.md) 를 보고 준비하면 됩니다.

`Dtumos()` 는 환경변수 `SMARTMOB_DTUMOS_URL` 이 설정되어 있을 때만 서버에 접속을 시도합니다. 설정하지 않았다면 서버를 찾지 않고 곧바로 내장 엔진을 씁니다. 지금은 설정하지 않은 상태이므로 아무것도 하지 않아도 됩니다.

```{code-cell} python
from smartmob import Dtumos

dt = Dtumos()
dt.health()
```

`status` 가 `local` 이면 내장 엔진으로 도는 중입니다. 이 상태가 정상입니다.

내장 엔진에는 두 종류의 결과가 있습니다. 이 책이 기준으로 삼는 실험 하나는 실제 DTUMOS 를 돌린 결과가 `data/fixtures/` 에 저장되어 있습니다. 그 조건으로 부르면 저장된 결과를 그대로 돌려줍니다. 조건을 바꾸면 내장 엔진이 새로 계산합니다.

```{note}
내장 엔진은 도로망을 달리지 않습니다. 두 점 사이 직선거리를 시속 25km 로 나눈 시간을 씁니다. 그래서 차량 대수를 80대에서 40대로 바꾸면 나오는 숫자는 근사값입니다. 이 근사가 실제 엔진과 얼마나 가까운지는 11장에서 직접 확인합니다. 평균 대기시간 기준으로 0.2분 안쪽입니다.
```

```{note}
수업에서 공용 서버를 쓴다면 `SMARTMOB_DTUMOS_URL` 에 안내받은 주소를 넣습니다. 환경변수 설정 명령은 운영체제와 셸에 따라 다릅니다. 설정 뒤에는 주피터 커널을 다시 시작하고 `dt.health()` 의 `status` 가 `healthy` 로 바뀌는지 확인합니다.
```

## 0.4 첫 시뮬레이션

하남시에서 저녁 6시부터 자정까지, 택시 80대로 1,000건의 호출을 처리해 봅니다. `1080` 은 자정부터의 분이고 18:00입니다. 이 책의 시간은 전부 이 단위입니다.

```{code-cell} python
sim = dt.run_simulation(
    city="hanam",
    mode="taxi",
    fleet_size=80,
    num_passengers=1000,
    time_start=1080,   # 18:00
    time_end=1440,     # 24:00
    random_seed=42,
)
sim.summary()
```

```{note}
`Dtumos` 는 시뮬레이션 서버에 요청을 보내는 **클래스**입니다. `dt = Dtumos()` 는 이 클래스에서 객체 `dt` 를 만듭니다. `dt.run_simulation(...)` 은 객체에 정의된 동작인 메서드이고, 실행 결과는 `sim` 이라는 새 객체에 담깁니다.

`sim.summary()` 처럼 괄호가 붙은 것은 값을 계산하는 메서드입니다. `sim.record` 처럼 괄호가 없으면 객체가 이미 가지고 있는 자료를 속성으로 꺼냅니다.
```

숫자를 하나씩 읽어 봅니다.

- `service_rate` 가 1.0입니다. 990건의 호출이 전부 배차됐습니다. 1,000건을 넣었는데 990건인 것은, 마지막 열 건이 23시 56분 이후에 들어온 호출이라 자정에 끝나는 시뮬레이션이 세지 않기 때문입니다. 이 990이라는 숫자는 뒤의 장에서 계속 나옵니다.
- `avg_waiting_time_min` 이 약 4.1분입니다. 호출하고 차가 올 때까지 평균 4분 걸렸습니다.
- `utilization` 이 약 0.27입니다. 차량이 승객을 태우고 있던 시간이 전체의 27%뿐입니다.

마지막 값이 흥미롭습니다. 대기시간이 4분이면 승객 입장에서는 괜찮은데, 차량의 4분의 3은 놀고 있었습니다. 80대가 너무 많은 것은 아닐까요? 40대로 줄이면 대기시간이 얼마나 늘어날까요?

이 질문에 답하려면 같은 수요와 같은 도로망 위에서 차량 대수만 바꿔 다시 돌려 봐야 합니다. 그 도구를 이 책에서 만듭니다.

## 0.5 분 단위 운행 기록 읽기

결과 객체에는 표가 둘 있습니다. `sim.record` 는 1분마다 한 줄씩 기록된 표이고, 컬럼 이름이 `_cnt` 로 끝납니다. `sim.result` 는 같은 시각을 차량 상태별로 더 잘게 나눈 표이고, 컬럼 이름이 `_num` 으로 끝납니다. 이 장에서는 `record` 만 보고, `result` 는 1장에서 씁니다.

```{code-cell} python
sim.record.head()
```

`waiting_passenger_cnt` 가 그 분에 기다리고 있던 승객 수입니다. `empty_vehicle_cnt` 는 빈 차, `driving_vehicle_cnt` 는 운행 중인 차의 수입니다. `fail_passenger_cnt` 는 배차를 못 받고 포기한 승객의 누적 수입니다.

그림으로 봅니다.

```{code-cell} python
from smartmob.viz import plot_record

plot_record(sim.record);
```

운행 중 차량이 늘어난 만큼 대기 중 차량이 줄어듭니다. 둘을 더하면 대부분의 시간에 80이 됩니다.

그런데 마지막 30분쯤에서 합이 80보다 작아지고, 대기 승객 수는 오히려 늘어납니다. 근무 시간이 끝난 차량이 하나씩 빠지기 때문입니다. 차량마다 `work_start` 와 `work_end` 가 정해져 있고, 자정이 가까워지면 남는 차가 줄어듭니다.

```{code-cell} python
on_duty = sim.record["empty_vehicle_cnt"] + sim.record["driving_vehicle_cnt"]
print("근무 중 차량 최대:", on_duty.max())
print("근무 중 차량 최소:", on_duty.min())
print("마지막 시각 대기 승객:", sim.record["waiting_passenger_cnt"].iloc[-1])
```

시뮬레이션이 "차량 80대"를 항상 80대로 다루지 않는다는 뜻입니다. 이런 것을 미리 알고 있어야 결과를 잘못 읽지 않습니다.

## 이 장의 실습

노트북 `labs/ch00_setup.ipynb` 를 열어 함께 돌립니다.

설치 확인부터 첫 시뮬레이션까지 이 장의 순서를 그대로 따라갑니다. 마지막에 빈칸이 하나 있습니다.

```bash
jupyter lab labs/ch00_setup.ipynb
```

가상환경을 활성화한 터미널에서 띄워야 노트북이 `.venv` 의 파이썬을 씁니다. 노트북에서 `ModuleNotFoundError` 가 나면 대부분 이것 때문입니다.

```{admonition} AI 에게 물어보기 — 빈칸이 안 풀릴 때
:class: tip

답을 그대로 받으면 배울 자리가 사라집니다. 무엇을 모르는지 좁혀 달라고 부탁합니다.

> 아래 코드에서 오류가 났어. 원인이 어디인지만 짚어 주고 고친 코드는 주지 마.

> 이 빈칸을 채우려면 어떤 함수를 찾아봐야 하는지 이름만 알려 줘.

> 내가 쓴 코드가 왜 이 값을 내는지 한 줄씩 따라가면서 설명해 줘.
```

## 정리

- `pip install -r requirements.txt` 로 환경을 만들고, `smartmob` 을 통해 데이터와 엔진에 접근합니다
- `load_road_graph("hanam")` 이 도로망을, `Dtumos()` 가 시뮬레이션 엔진을 담당합니다
- 엔진은 서버 없이 노트북 안에서 돕니다. `SMARTMOB_DTUMOS_URL` 을 설정할 때만 DTUMOS 서버를 씁니다
- `sim.summary()` 는 서비스율·평균 대기시간·차량 가동률을, `sim.record` 는 분 단위 시계열을 줍니다
- 설치가 끝나면 `import smartmob`과 각 절의 확인 코드를 실행합니다
- 1장에서는 이 장치가 왜 필요한지, 기존 시뮬레이터로는 왜 안 되는지를 봅니다

## 연습문제

```{admonition} 연습 0.1  ★
:class: tip

`sim.record` 에서 대기 승객 수가 가장 많았던 시각과 그때의 인원을 구해 봅시다.
`smartmob.data.minutes_to_hhmm` 을 쓰면 분을 `HH:MM` 으로 바꿀 수 있습니다.

산출물: 시각 1개, 인원 1개.
```
