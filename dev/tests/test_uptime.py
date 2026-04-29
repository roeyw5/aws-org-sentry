"""Tests for uptime calculation."""

import pytest
from datetime import datetime, timedelta, timezone
from scanner.utils import calculate_uptime


def test_calculate_uptime_basic():
    """Test basic uptime calculation with compact format."""
    # 13 hours 44 minutes ago
    launch_time = datetime.now(timezone.utc) - timedelta(hours=13, minutes=44)
    total_seconds, formatted = calculate_uptime(launch_time)

    assert total_seconds >= 49440  # 13*3600 + 44*60
    assert total_seconds < 49500  # Allow small time drift
    # Compact format shows hours only (no minutes)
    assert formatted == "13h"


def test_calculate_uptime_zero():
    """Test uptime calculation for just-launched resource."""
    launch_time = datetime.now(timezone.utc)
    total_seconds, formatted = calculate_uptime(launch_time)

    assert total_seconds >= 0
    assert total_seconds < 60
    assert "0h" in formatted


def test_calculate_uptime_hours_only():
    """Test uptime with no minutes component - compact format."""
    launch_time = datetime.now(timezone.utc) - timedelta(hours=5, minutes=0)
    total_seconds, formatted = calculate_uptime(launch_time)

    assert total_seconds >= 18000  # 5*3600
    # Compact format shows "5h" not "5h 0m"
    assert formatted == "5h"


def test_calculate_uptime_days():
    """Test uptime calculation for multi-day resources - compact format."""
    launch_time = datetime.now(timezone.utc) - timedelta(days=2, hours=3, minutes=15)
    total_seconds, formatted = calculate_uptime(launch_time)

    expected_seconds = 2 * 86400 + 3 * 3600 + 15 * 60
    assert total_seconds >= expected_seconds
    # Compact format shows "2d 3h" not "51h"
    assert formatted == "2d 3h"


def test_calculate_uptime_future_raises_error():
    """Test that future launch time raises ValueError."""
    future_time = datetime.now(timezone.utc) + timedelta(hours=1)

    with pytest.raises(ValueError, match="future"):
        calculate_uptime(future_time)
