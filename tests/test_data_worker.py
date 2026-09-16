import json

import crypto_widgetV5 as widget

ASSET = {
    "id": "bitcoin",
    "symbol": "BTC",
    "yf_symbol": "BTC-USD",
    "color": "#F7931A",
    "scale": 1.0,
}


def test_network_failure_returns_cached_price(tmp_path, monkeypatch):
    cache_path = tmp_path / "prices.json"
    cache_path.write_text(json.dumps({
        "version": 1,
        "prices": {
            "bitcoin": {
                "id": "bitcoin",
                "symbol": "BTC",
                "current_price": 65000,
                "price_change_percentage_24h": 1.5,
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        },
    }), encoding="utf-8")

    def fail_download(*_args, **_kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(widget.yf, "download", fail_download)
    monkeypatch.setattr(widget.time, "sleep", lambda _seconds: None)
    worker = widget.DataWorker([ASSET], "usd", cache_path)
    results = []
    errors = []
    finished = []
    worker.data_updated.connect(results.append)
    worker.error_occurred.connect(errors.append)
    worker.finished.connect(lambda: finished.append(True))

    worker.run()

    assert errors == []
    assert finished == [True]
    assert results[0]["stale"] is True
    assert results[0]["prices"][0]["cached"] is True
    assert results[0]["prices"][0]["current_price"] == 65000


def test_network_failure_without_cache_emits_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        widget.yf, "download", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("offline"))
    )
    monkeypatch.setattr(widget.time, "sleep", lambda _seconds: None)
    worker = widget.DataWorker([ASSET], "usd", tmp_path / "missing.json")
    errors = []
    worker.error_occurred.connect(errors.append)

    worker.run()

    assert errors == ["offline"]
