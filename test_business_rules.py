from datetime import date

from calculations import calculate_derived_fields
from scrapers.screener import should_fetch_after_quarter_check


def test_target_consensus_and_sotp_are_not_derived():
    data = {
        "current_price": 100,
        "target_price_high": 150,
        "target_price_low": 90,
    }

    result = calculate_derived_fields(data)

    assert "consensus_target_price" not in result
    assert "consensus_upside_pct" not in result
    assert "sotp_value" not in result
    assert result["potential_upside_high"] == 50
    assert result["potential_upside_low"] == -10


def test_quarter_check_fetches_only_when_stale_or_changed():
    today = date(2026, 5, 15)

    assert not should_fetch_after_quarter_check("2026-03-31", "2026-03-31", today=today)
    assert should_fetch_after_quarter_check("2026-03-31", "2026-06-30", today=today)
    assert should_fetch_after_quarter_check("2025-12-31", "2025-12-31", today=today)
