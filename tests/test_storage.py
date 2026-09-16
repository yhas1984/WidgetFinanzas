from crypto_widgetV5 import read_json, write_json_atomic


def test_atomic_json_round_trip(tmp_path):
    path = tmp_path / "nested" / "state.json"

    assert write_json_atomic(path, {"x": 10, "y": 20}) is True
    assert read_json(path) == {"x": 10, "y": 20}
