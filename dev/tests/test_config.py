"""Tests for configuration loading."""

import pytest
import boto3
import json
from moto import mock_ssm
from scanner.config import Config, get_config, _config_cache


@mock_ssm
def test_config_loads_all_parameters():
    """Test that Config loads all required parameters from Parameter Store."""
    ssm = boto3.client("ssm", region_name="us-east-1")

    # Create test parameters
    base_path = "/org-scanner/dev"
    ssm.put_parameter(
        Name=f"{base_path}/slack-token", Value="xoxb-test-token", Type="SecureString"
    )
    ssm.put_parameter(
        Name=f"{base_path}/monitoring-channel", Value="C12345", Type="String"
    )
    ssm.put_parameter(
        Name=f"{base_path}/users-mapping",
        Value=json.dumps(
            {"Account.Test": {"id": "123456789012", "email": "test@example.com"}}
        ),
        Type="SecureString",
    )
    ssm.put_parameter(Name=f"{base_path}/ou-id", Value="ou-test-12345", Type="String")
    ssm.put_parameter(
        Name=f"{base_path}/regions", Value="ap-south-1,us-east-1", Type="String"
    )
    ssm.put_parameter(
        Name=f"{base_path}/scan-toggles",
        Value=json.dumps({"ec2": True, "rds": True, "eks": False}),
        Type="String",
    )

    # Load config
    config = Config("dev")

    # Verify all values
    assert config.slack_token == "xoxb-test-token"
    assert config.monitoring_channel == "C12345"
    assert config.users_mapping == {
        "Account.Test": {"id": "123456789012", "email": "test@example.com"}
    }
    assert config.ou_id == "ou-test-12345"
    assert config.regions == ["ap-south-1", "us-east-1"]
    assert config.scan_toggles == {"ec2": True, "rds": True, "eks": False}


@mock_ssm
def test_config_caching():
    """Test that get_config() caches configuration."""
    ssm = boto3.client("ssm", region_name="us-east-1")

    # Create minimal parameters
    base_path = "/org-scanner/dev"
    ssm.put_parameter(
        Name=f"{base_path}/slack-token", Value="token", Type="SecureString"
    )
    ssm.put_parameter(
        Name=f"{base_path}/monitoring-channel", Value="C12345", Type="String"
    )
    ssm.put_parameter(
        Name=f"{base_path}/users-mapping", Value="{}", Type="SecureString"
    )
    ssm.put_parameter(Name=f"{base_path}/ou-id", Value="ou-123", Type="String")
    ssm.put_parameter(Name=f"{base_path}/regions", Value="ap-south-1", Type="String")
    ssm.put_parameter(Name=f"{base_path}/scan-toggles", Value="{}", Type="String")

    # Clear cache
    _config_cache.clear()

    # First call should load from SSM
    config1 = get_config("dev")
    assert "dev" in _config_cache

    # Second call should return cached instance
    config2 = get_config("dev")
    assert config1 is config2


@mock_ssm
def test_config_missing_parameter_raises_error():
    """Test that missing parameter raises exception."""
    ssm = boto3.client("ssm", region_name="us-east-1")

    # Create incomplete parameters (missing slack-token)
    base_path = "/org-scanner/dev"
    ssm.put_parameter(Name=f"{base_path}/ou-id", Value="ou-123", Type="String")

    with pytest.raises(ValueError, match="Required parameter not found"):
        Config("dev")


@mock_ssm
def test_config_regions_parsing():
    """Test that regions string is parsed correctly."""
    ssm = boto3.client("ssm", region_name="us-east-1")

    base_path = "/org-scanner/test"
    ssm.put_parameter(
        Name=f"{base_path}/slack-token", Value="token", Type="SecureString"
    )
    ssm.put_parameter(
        Name=f"{base_path}/monitoring-channel", Value="C12345", Type="String"
    )
    ssm.put_parameter(
        Name=f"{base_path}/users-mapping", Value="{}", Type="SecureString"
    )
    ssm.put_parameter(Name=f"{base_path}/ou-id", Value="ou-123", Type="String")
    ssm.put_parameter(
        Name=f"{base_path}/regions",
        Value="us-east-1, eu-west-1 ,ap-south-1",  # With spaces
        Type="String",
    )
    ssm.put_parameter(Name=f"{base_path}/scan-toggles", Value="{}", Type="String")

    config = Config("test")
    assert config.regions == ["us-east-1", "eu-west-1", "ap-south-1"]
