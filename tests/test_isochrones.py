"""등시선의 시간 경계, 빈 영역, 다중 경계 보존을 확인합니다."""

import pytest
from shapely.geometry import Point, Polygon

from smartmob.viz.isochrones import isochrone_shapes


def filled_area(rings):
    area = Polygon()
    for ring in rings:
        area = area.symmetric_difference(Polygon(ring))
    return area


def test_linear_time_field_produces_known_contours_and_bands():
    points = [[0, 0], [100, 0], [0, 100], [100, 100]]
    result = isochrone_shapes(points, [0, 100, 0, 100], [25, 75], max_gap_m=200)
    first, second = result["bands"]
    for band in result["bands"]:
        assert band["lines"]
        # The analytic field is t(x,y)=x, so a t-second isoline must have x=t.
        assert all(x == band["seconds"] for line in band["lines"] for x, _ in line)
    assert filled_area(first["rings"]).area == pytest.approx(2500)
    assert filled_area(second["rings"]).area == pytest.approx(5000)
    assert not filled_area(first["rings"]).contains(Point(50, 50))


def test_unreachable_vertices_and_long_gaps_are_not_interpolated():
    points = [[0, 0], [100, 0], [0, 100]]
    for times, gap in [([0, 100, None], 200), ([0, 100, 100], 50)]:
        result = isochrone_shapes(points, times, [50], max_gap_m=gap)
        assert not result["bands"] and result["reason"]
        assert result["maskedTriangles"] == 1


def test_masked_hole_survives_exported_polygon_rings():
    points = [[x, y] for y in range(0, 401, 100) for x in range(0, 401, 100)]
    times = [None if (x, y) == (200, 200) else x for x, y in points]
    result = isochrone_shapes(points, times, [500], max_gap_m=200)
    band = result["bands"][0]
    area = filled_area(band["rings"])
    assert area.is_valid and len(band["rings"]) >= 2
    assert not area.covers(Point(200, 200))
    assert area.covers(Point(25, 25))
    # The time field never reaches 500; the data/mask boundary is NOT a 500 s isoline.
    assert not band["lines"]


def test_collinear_or_coincident_nodes_fall_back_to_node_map():
    for points in [[[0, 0]] * 3, [[0, 0], [1, 1], [2, 2]]]:
        result = isochrone_shapes(points, [0, 1, 2], [1])
        assert not result["bands"] and result["reason"]


def test_coincident_coordinates_take_the_smallest_known_time():
    result = isochrone_shapes(
        [[0, 0], [100, 0], [0, 100], [0, 0]], [None, 100, 0, 0], [25], max_gap_m=200
    )
    assert result["bands"][0]["lines"]
    assert all(x == 25 for line in result["bands"][0]["lines"] for x, _ in line)
