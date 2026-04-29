"""Tests for RDS scanning."""

import boto3
from moto import mock_rds
from scanner.rds import scan_rds_instances


@mock_rds
def test_scan_rds_instances():
    """Test RDS scanning finds databases."""
    rds = boto3.client("rds", region_name="us-east-1")

    # Create DB instance
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="mysql",
        MasterUsername="admin",
        MasterUserPassword="password123",
    )

    # Scan
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    databases = scan_rds_instances(credentials, "us-east-1")

    assert len(databases) == 1
    assert databases[0]["id"] == "test-db"
    assert databases[0]["name"] == "test-db"
    assert databases[0]["class"] == "db.t3.micro"
    assert databases[0]["status"] == "available"
    assert "create_time" in databases[0]


@mock_rds
def test_scan_rds_instances_empty():
    """Test RDS scanning with no databases."""
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    databases = scan_rds_instances(credentials, "us-west-2")

    assert databases == []


@mock_rds
def test_scan_rds_instances_multiple():
    """Test RDS scanning finds multiple databases."""
    rds = boto3.client("rds", region_name="us-east-1")

    # Create multiple DB instances
    for i in range(3):
        rds.create_db_instance(
            DBInstanceIdentifier=f"test-db-{i}",
            DBInstanceClass="db.t3.small",
            Engine="postgres",
            MasterUsername="admin",
            MasterUserPassword="password123",
        )

    # Scan
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    databases = scan_rds_instances(credentials, "us-east-1")

    assert len(databases) == 3
    db_ids = [db["id"] for db in databases]
    assert "test-db-0" in db_ids
    assert "test-db-1" in db_ids
    assert "test-db-2" in db_ids
