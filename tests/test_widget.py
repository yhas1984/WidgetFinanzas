from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QApplication

from crypto_widgetV5 import CryptoWidget


def test_zero_previous_price_does_not_crash(tmp_path, monkeypatch):
    config_home = tmp_path / "config"
    data_home = tmp_path / "data"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_DATA_HOME", str(data_home))
    legacy = data_home / "applications" / "crypto_widget.desktop"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(
        "[Desktop Entry]\nName=Crypto Widget\nExec=crypto_widget.py\n",
        encoding="utf-8",
    )
    app = QApplication.instance() or QApplication([])
    config = {
        "currency": "usd",
        "update_interval_seconds": 3600,
        "run_on_startup": False,
        "desktop_mode": False,
        "assets": [],
        "icons": {},
        "window_width": 500,
        "window_height": 50,
        "position": "top-center",
    }
    window = CryptoWidget(config, tmp_path / "prices.json", tmp_path / "window.json")
    for _ in range(100):
        app.processEvents()
        if window.thread is None:
            break
        QThread.msleep(1)
    window.config["assets"] = [{
        "id": "zero",
        "symbol": "ZERO",
        "color": "#FFFFFF",
        "yf_symbol": "ZERO",
    }]
    window.previous_prices = {"zero": 0.0}

    window.update_ui({
        "prices": [{
            "id": "zero",
            "current_price": 1.0,
            "price_change_percentage_24h": 1.0,
            "cached": False,
        }]
    })

    assert window.previous_prices["zero"] == 1.0
    assert not legacy.exists()
    window.move(123, 234)
    window.save_position()
    saved = (tmp_path / "window.json").read_text(encoding="utf-8")
    assert '"x": 123' in saved
    assert '"y": 234' in saved
    window.close()
    for _ in range(100):
        app.processEvents()
        if window.thread is None:
            break
        QThread.msleep(1)
    assert window.thread is None
