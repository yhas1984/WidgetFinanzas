from crypto_widgetV5 import format_price


def test_price_format_uses_asset_quote_currency():
    assert format_price(1234.5, {"quote_currency": "eur"}) == "€1,234"
    assert format_price(1.2345, {"quote_currency": "points"}) == "1.23"
    assert format_price(0.123456, {}, "usd") == "$0.1235"
