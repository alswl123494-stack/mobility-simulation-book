"""도로망 노드의 최단시간을 선형 보간한 교육용 등시선.

계산된 도로망 통행시간과 도로 밖의 보간 결과를 구분합니다. 긴 삼각형과
도달 불가능한 꼭짓점을 포함하는 삼각형은 제외하며, 지형 장벽은 모델링하지 않습니다.
"""

from __future__ import annotations

import math


def _parts(path, *, closed=False):
    from matplotlib.path import Path

    parts, current = [], []
    for vertices, code in path.iter_segments(simplify=False, curves=False):
        if code == Path.MOVETO:
            if current:
                parts.append(current)
            current = [[round(float(v), 1) for v in vertices]]
        elif code == Path.LINETO:
            current.append([round(float(v), 1) for v in vertices])
        elif code == Path.CLOSEPOLY and current:
            if current[-1] != current[0]:
                current.append(current[0])
            parts.append(current)
            current = []
    if current:
        parts.append(current)
    if closed:
        return [p for p in parts if len(p) >= 4 and p[0] == p[-1]]
    return [p for p in parts if len(p) >= 2]


def isochrone_shapes(points, seconds, levels, *, max_gap_m=500.0):
    """미터 단위 좌표와 확정 시간에서 등시선·등시간대 좌표를 만듭니다.

    ``seconds``의 None은 도달 불가능한 노드입니다. 시간 상한 밖의 노드도
    실제 최단시간을 넣어야 경계가 보간됩니다. None을 상한 초과의 대용으로 쓰지 않습니다.
    이 결과는 도로 밖의 접근성을 보장하는 서비스 구역이 아닙니다.
    """
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.tri import Triangulation

    if len(points) != len(seconds):
        raise ValueError("좌표와 시간의 개수가 다릅니다.")
    levels = sorted(set(float(t) for t in levels))
    if not levels or any(not math.isfinite(t) or t <= 0 for t in levels):
        raise ValueError("등시선의 시간은 유한한 양수여야 합니다.")
    if not math.isfinite(max_gap_m) or max_gap_m <= 0:
        raise ValueError("보간할 최대 간격은 유한한 양수여야 합니다.")

    # A single interpolated surface needs one value at coincident coordinates.
    unique = {}
    for point, value in zip(points, seconds):
        if len(point) != 2 or not all(math.isfinite(v) for v in point):
            raise ValueError("좌표는 유한한 x, y 값이어야 합니다.")
        if value is not None and (not math.isfinite(value) or value < 0):
            raise ValueError("확정 시간은 0 이상이거나 도달 불가능을 뜻하는 None입니다.")
        key = tuple(point)
        unique[key] = min(unique.get(key, math.inf), value if value is not None else math.inf)

    result = {"maxGapM": max_gap_m, "bands": [], "reason": "", "maskedTriangles": 0}
    coords = np.asarray(list(unique), dtype=float)
    if len(coords) < 3 or np.linalg.matrix_rank(coords - coords[0]) < 2:
        result["reason"] = "서로 다른 위치의 노드가 부족해 등시선을 보간할 수 없습니다."
        return result
    values = np.asarray(list(unique.values()), dtype=float)
    tri = Triangulation(coords[:, 0], coords[:, 1])
    vertices = coords[tri.triangles]
    longest = np.sqrt(((vertices - np.roll(vertices, 1, axis=1)) ** 2).sum(axis=2)).max(axis=1)
    mask = (~np.isfinite(values[tri.triangles])).any(axis=1) | (longest > max_gap_m)
    result["maskedTriangles"] = int(mask.sum())
    if mask.all():
        result["reason"] = "노드 사이 간격이나 도달 여부 때문에 보간할 영역이 없습니다."
        return result
    tri.set_mask(mask)
    values[~np.isfinite(values)] = 0  # These vertices occur only in masked triangles.
    valid = values[np.unique(tri.triangles[~mask])]
    figure = Figure()
    axes = figure.subplots()
    fills = axes.tricontourf(tri, values, levels=[-1e-9, *levels])
    for i, level in enumerate(levels):
        lines = []
        if valid.min() < level < valid.max():
            contours = axes.tricontour(tri, values, levels=[level])
            lines = _parts(contours.get_paths()[0])
            contours.remove()
        result["bands"].append({
            "seconds": level,
            "lowerSeconds": levels[i - 1] if i else 0,
            "rings": _parts(fills.get_paths()[i], closed=True),
            "lines": lines,
        })
    figure.clear()
    return result
