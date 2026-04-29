"""Unit tests for threshold loading and validation."""

from scanner.slack import (
    _get_thresholds,
    _validate_threshold,
    _validate_count_threshold
)


def test_get_thresholds_all_defaults():
    """Test all 16 default thresholds load correctly."""
    thresholds = _get_thresholds()

    # Time (hours → seconds)
    assert thresholds["ec2_running"] == 12 * 3600
    assert thresholds["ec2_stopped"] == 672 * 3600
    assert thresholds["rds"] == 5 * 3600
    assert thresholds["eks"] == 12 * 3600

    # Time (hours → seconds)
    assert thresholds["eip"] == 2 * 3600
    assert thresholds["lightsail"] == 168 * 3600
    assert thresholds["volume"] == 672 * 3600
    assert thresholds["rds_snapshot"] == 2160 * 3600

    # Count
    assert thresholds["nat_gateway"] == 0
    assert thresholds["elb"] == 0

    # Count
    assert thresholds["volume_count"] == 5
    assert thresholds["eip_count"] == 2
    assert thresholds["vpc_endpoint"] == 2
    assert thresholds["lightsail_count"] == 1
    assert thresholds["ebs_snapshot"] == 10
    assert thresholds["rds_snapshot_count"] == 5


def test_get_thresholds_custom_values(monkeypatch):
    """Test custom threshold values from environment."""
    monkeypatch.setenv("THRESHOLD_EIP_HOURS", "1")
    monkeypatch.setenv("THRESHOLD_LIGHTSAIL_COUNT", "3")
    monkeypatch.setenv("THRESHOLD_EBS_SNAPSHOT_COUNT", "50")

    thresholds = _get_thresholds()

    assert thresholds["eip"] == 1 * 3600  # Custom
    assert thresholds["lightsail_count"] == 3  # Custom
    assert thresholds["ebs_snapshot"] == 50  # Custom
    assert thresholds["ec2_running"] == 12 * 3600  # Default (not overridden)


def test_validate_threshold_valid_hours():
    """Test validation with valid hour values."""
    assert _validate_threshold("12", 24) == 12 * 3600
    assert _validate_threshold("0", 24) == 0  # Zero is valid
    assert _validate_threshold("2160", 24) == 2160 * 3600  # Large value


def test_validate_threshold_invalid_values():
    """Test validation with invalid values."""
    assert _validate_threshold("abc", 12) == 12 * 3600  # String → default
    assert _validate_threshold("-5", 12) == 12 * 3600  # Negative → default
    assert _validate_threshold(None, 12) == 12 * 3600  # None → default
    assert _validate_threshold("", 12) == 12 * 3600  # Empty → default


def test_validate_count_threshold_valid_counts():
    """Test count validation with valid values."""
    assert _validate_count_threshold("1", 5) == 1
    assert _validate_count_threshold("0", 5) == 0  # Zero is valid
    assert _validate_count_threshold("100", 5) == 100  # Large value


def test_validate_count_threshold_invalid_values():
    """Test count validation with invalid values."""
    assert _validate_count_threshold("abc", 5) == 5  # String → default
    assert _validate_count_threshold("-10", 5) == 5  # Negative → default
    assert _validate_count_threshold(None, 5) == 5  # None → default


def test_threshold_structure():
    """Test that thresholds dict has all expected keys."""
    thresholds = _get_thresholds()

    # Time-based keys
    assert "ec2_running" in thresholds
    assert "ec2_stopped" in thresholds
    assert "rds" in thresholds
    assert "eks" in thresholds
    assert "eip" in thresholds
    assert "lightsail" in thresholds
    assert "volume" in thresholds
    assert "rds_snapshot" in thresholds

    # Count-based keys
    assert "nat_gateway" in thresholds
    assert "elb" in thresholds
    assert "volume_count" in thresholds
    assert "eip_count" in thresholds
    assert "vpc_endpoint" in thresholds
    assert "lightsail_count" in thresholds
    assert "ebs_snapshot" in thresholds
    assert "rds_snapshot_count" in thresholds

    # All thresholds are positive integers
    for key, value in thresholds.items():
        assert isinstance(value, int), f"{key} should be an integer"
        assert value >= 0, f"{key} should be non-negative"


def test_get_thresholds_all_custom_values(monkeypatch):
    """Test all 16 thresholds can be customized."""
    # Set all environment variables
    monkeypatch.setenv("THRESHOLD_EC2_RUNNING_HOURS", "10")
    monkeypatch.setenv("THRESHOLD_EC2_STOPPED_HOURS", "30")
    monkeypatch.setenv("THRESHOLD_RDS_HOURS", "20")
    monkeypatch.setenv("THRESHOLD_EKS_HOURS", "20")
    monkeypatch.setenv("THRESHOLD_EIP_HOURS", "1")
    monkeypatch.setenv("THRESHOLD_LIGHTSAIL_HOURS", "120")
    monkeypatch.setenv("THRESHOLD_VOLUME_HOURS", "120")
    monkeypatch.setenv("THRESHOLD_RDS_SNAPSHOT_HOURS", "1800")

    monkeypatch.setenv("THRESHOLD_NAT_GATEWAY_COUNT", "2")
    monkeypatch.setenv("THRESHOLD_ELB_COUNT", "2")
    monkeypatch.setenv("THRESHOLD_VOLUME_COUNT", "10")
    monkeypatch.setenv("THRESHOLD_EIP_COUNT", "3")
    monkeypatch.setenv("THRESHOLD_VPC_ENDPOINT_COUNT", "3")
    monkeypatch.setenv("THRESHOLD_LIGHTSAIL_COUNT", "2")
    monkeypatch.setenv("THRESHOLD_EBS_SNAPSHOT_COUNT", "30")
    monkeypatch.setenv("THRESHOLD_RDS_SNAPSHOT_COUNT", "15")

    thresholds = _get_thresholds()

    # Verify all custom values
    assert thresholds["ec2_running"] == 10 * 3600
    assert thresholds["ec2_stopped"] == 30 * 3600
    assert thresholds["rds"] == 20 * 3600
    assert thresholds["eks"] == 20 * 3600
    assert thresholds["eip"] == 1 * 3600
    assert thresholds["lightsail"] == 120 * 3600
    assert thresholds["volume"] == 120 * 3600
    assert thresholds["rds_snapshot"] == 1800 * 3600

    assert thresholds["nat_gateway"] == 2
    assert thresholds["elb"] == 2
    assert thresholds["volume_count"] == 10
    assert thresholds["eip_count"] == 3
    assert thresholds["vpc_endpoint"] == 3
    assert thresholds["lightsail_count"] == 2
    assert thresholds["ebs_snapshot"] == 30
    assert thresholds["rds_snapshot_count"] == 15
