import math

import pytest

from backend.services import statistics as st
from backend.services.spatial import bounding_box, haversine_km, haversine_sql, valid_coordinate


def test_haversine_known_distance():
    # Calgary City Hall -> Edmonton Legislature is ~280 km great-circle
    d = haversine_km(51.0447, -114.0631, 53.5344, -113.5065)
    assert 275 < d < 285
    assert haversine_km(51, -114, 51, -114) == 0


def test_haversine_uses_lat_lon_order_and_kilometres():
    one_deg_lat = haversine_km(50, -114, 51, -114)
    assert one_deg_lat == pytest.approx(111.19, abs=0.2)
    # a degree of longitude is shorter at 51N than at the equator
    assert haversine_km(51, -114, 51, -113) < haversine_km(0, 0, 0, 1)


@pytest.mark.parametrize("radius", [1, 5, 20])
def test_bounding_box_contains_the_circle(radius):
    lat, lon = 51.19, -114.47
    box = bounding_box(lat, lon, radius)
    for bearing in range(0, 360, 15):
        # point exactly `radius` km away
        dlat = math.degrees(radius / 6371.0088) * math.cos(math.radians(bearing))
        dlon = math.degrees(radius / (6371.0088 * math.cos(math.radians(lat)))) * math.sin(math.radians(bearing))
        assert box["min_lat"] <= lat + dlat <= box["max_lat"]
        assert box["min_lon"] <= lon + dlon <= box["max_lon"]


def test_valid_coordinate():
    assert valid_coordinate(51.2, -114.5)
    assert not valid_coordinate(None, -114)
    assert not valid_coordinate(91, 0)
    assert not valid_coordinate(0, 0)
    assert not valid_coordinate(float("nan"), 1)


def test_haversine_sql_binds_parameters_only():
    sql = haversine_sql("`lat`", "`lon`")
    assert ":lat" in sql and ":lon" in sql and "51" not in sql


# ---------------------------------------------------------------- statistics
def test_median_ignores_none_and_never_treats_missing_as_zero():
    assert st.median([None, 10, 20, None]) == 15
    assert st.median([3, None, 1, 2]) == 2
    assert st.median([None, None]) is None
    assert st.median([]) is None
    assert st.median([0, 0, 10]) == 0  # real zeros are kept


def test_histogram_bins_and_open_ended_last_bin():
    counts = st.count_bins([1, 24.9, 25, 99, 1000, None], width=25, n_bins=4)
    assert counts == {0: 2, 1: 1, 3: 2}
    h = st.build_histogram(counts, 25, 4, "m")
    assert [b.count for b in h.bins] == [2, 1, 0, 2]
    assert h.bins[-1].label == "75+" and h.bins[-1].end is None
    assert h.sample_count == 5 and h.unit == "m"


def test_empty_histogram_has_no_bins():
    assert st.build_histogram({}, 25, 4, "m").bins == []


def test_sufficiency_message_is_honest():
    limited, notes = st.assess_sufficiency(total=2, depth_n=2, yield_n=0, min_sample=5)
    assert limited and "Limited historical information" in notes[0]
    assert st.assess_sufficiency(50, 40, 40, 5) == (False, [])
