import json

from crypto_widgetV5 import DEFAULT_CONFIG, load_config, validate_config


def test_invalid_config_uses_safe_values():
    config, warnings = validate_config({
        "update_interval_seconds": 0,
        "window_width": "wide",
        "position": "middle",
        "assets": "BTC",
    })

    assert config["update_interval_seconds"] == DEFAULT_CONFIG["update_interval_seconds"]
    assert config["window_width"] == DEFAULT_CONFIG["window_width"]
    assert config["position"] == "top-center"
    assert config["assets"] == []
    assert warnings


def test_duplicate_and_incomplete_assets_are_rejected():
    asset = {"id": "btc", "symbol": "BTC", "yf_symbol": "BTC-USD"}
    config, warnings = validate_config({
        "assets": [asset, dict(asset), {"id": "broken"}],
    })

    assert [item["id"] for item in config["assets"]] == ["btc"]
    assert len(warnings) == 2


def test_user_config_overrides_bundled_config(tmp_path):
    app_dir = tmp_path / "app"
    app_dir.mkdir()
    (app_dir / "config.json").write_text(json.dumps({
        "update_interval_seconds": 60,
        "assets": [],
    }), encoding="utf-8")
    user_config = tmp_path / "user" / "config.json"
    user_config.parent.mkdir()
    user_config.write_text(json.dumps({
        "update_interval_seconds": 120,
        "position": "bottom-right",
    }), encoding="utf-8")

    config = load_config(app_dir, user_config)

    assert config["update_interval_seconds"] == 120
    assert config["position"] == "bottom-right"
