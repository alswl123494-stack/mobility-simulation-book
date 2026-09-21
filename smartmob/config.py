"""환경 설정.

환경변수 세 개로 동작이 결정됩니다.

``SMARTMOB_DTUMOS_URL``
    DTUMOS 서버 주소. **이 값을 설정해야만 서버에 접속합니다.**
    설정하지 않으면 :class:`~smartmob.client.Dtumos` 는 서버를 찾지 않고
    내장 파이썬 엔진으로 돕니다. 공용 서버를 쓸 때만 팀별 주소를 넣습니다.
    예: ``http://dtumos.example.ac.kr:8003``

``SMARTMOB_OFFLINE``
    ``1`` 이면 위 주소가 설정되어 있어도 접속하지 않습니다.
    책을 빌드하는 CI 는 항상 이 값을 설정합니다.

``SMARTMOB_DATA_DIR``
    데이터 디렉터리. 기본값은 저장소 루트의 ``data/``.

프로젝트 루트의 ``.env`` 파일이 있으면 읽습니다(python-dotenv 없이 동작).
"""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """저장소 루트. ``smartmob/`` 의 부모입니다."""
    return Path(__file__).resolve().parent.parent


def _load_dotenv() -> None:
    """루트의 .env 를 환경변수로 올립니다. 이미 설정된 값은 덮어쓰지 않습니다."""
    path = repo_root() / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


_load_dotenv()


DEFAULT_DTUMOS_URL = "http://localhost:8000"


def dtumos_url() -> str:
    """서버 주소. 설정하지 않았으면 기본값을 돌려줍니다."""
    return os.environ.get("SMARTMOB_DTUMOS_URL", DEFAULT_DTUMOS_URL).rstrip("/")


def dtumos_url_configured() -> bool:
    """서버 주소를 사람이 직접 설정했는지 알려 줍니다.

    설정하지 않았다면 서버를 쓸 의사가 없다고 보고 내장 엔진으로 돕니다.
    이 판정이 있어야, 다른 프로그램이 우연히 8000번 포트를 쓰고 있을 때
    책의 코드가 그 프로그램에 요청을 보내는 일이 생기지 않습니다.
    """
    return bool(os.environ.get("SMARTMOB_DTUMOS_URL", "").strip())


def offline() -> bool:
    return os.environ.get("SMARTMOB_OFFLINE", "").strip() in {"1", "true", "TRUE", "yes"}


def data_dir() -> Path:
    override = os.environ.get("SMARTMOB_DATA_DIR")
    return Path(override).resolve() if override else repo_root() / "data"


def fixtures_dir() -> Path:
    return data_dir() / "fixtures"
