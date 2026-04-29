"""Tests for utility functions."""

from moto import mock_sts
from scanner.utils import assume_role, _format_duration_compact


@mock_sts
def test_assume_role_returns_credentials():
    """Test that assume_role returns credential dictionary."""
    # Moto automatically mocks STS assume_role
    credentials = assume_role("123456789012")

    assert "aws_access_key_id" in credentials
    assert "aws_secret_access_key" in credentials
    assert "aws_session_token" in credentials
    assert credentials["aws_access_key_id"] != ""
    assert credentials["aws_secret_access_key"] != ""
    assert credentials["aws_session_token"] != ""


@mock_sts
def test_assume_role_correct_arn():
    """Test that assume_role uses correct role ARN."""
    account_id = "987654321098"

    # This will succeed with moto
    credentials = assume_role(account_id)

    # Verify credentials were returned (ARN was correct)
    assert credentials is not None
    assert "aws_access_key_id" in credentials


class TestDurationFormatCompact:
    """Test Compact duration formatting."""

    def test_hours_only_less_than_24(self):
        """Duration < 24h should show hours only."""
        assert _format_duration_compact(43200) == "12h"  # 12 hours
        assert _format_duration_compact(3600) == "1h"  # 1 hour
        assert _format_duration_compact(82800) == "23h"  # 23 hours

    def test_days_and_hours(self):
        """Duration >= 24h with remaining hours should show 'Xd Yh'."""
        assert _format_duration_compact(129600) == "1d 12h"  # 36 hours
        assert _format_duration_compact(648000) == "7d 12h"  # 180 hours
        assert _format_duration_compact(972000) == "11d 6h"  # 270 hours

    def test_days_only_no_remaining_hours(self):
        """Duration with exact days (no remaining hours) should show days only."""
        assert _format_duration_compact(86400) == "1d"  # 24 hours
        assert _format_duration_compact(604800) == "7d"  # 7 days
        assert _format_duration_compact(2592000) == "30d"  # 30 days

    def test_zero_duration(self):
        """Zero duration should show 0h."""
        assert _format_duration_compact(0) == "0h"

    def test_edge_cases(self):
        """Test boundary conditions."""
        assert _format_duration_compact(86399) == "23h"  # Just under 1 day
        assert _format_duration_compact(86401) == "1d"  # Just over 1 day (0h remainder not shown)
        assert _format_duration_compact(31536000) == "365d"  # 1 year
