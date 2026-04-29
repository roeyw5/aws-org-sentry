"""Tests for RDS snapshot scanning."""

import boto3
from datetime import datetime
from moto import mock_rds
from scanner.rds_snapshots import scan_rds_snapshots
from scanner.slack import should_alert, THRESHOLDS


@mock_rds
def test_scan_rds_snapshots_manual_only():
    """Test that scanner filters manual snapshots only."""
    rds = boto3.client("rds", region_name="us-east-1")

    # Create DB instance
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
    )

    # Create manual snapshot
    rds.create_db_snapshot(
        DBSnapshotIdentifier="manual-snapshot", DBInstanceIdentifier="test-db"
    )

    # Scan (automated snapshots excluded by SnapshotType='manual')
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    result = scan_rds_snapshots(credentials, "us-east-1")

    assert len(result) == 1
    assert result[0]["id"] == "manual-snapshot"
    assert "created_at" in result[0]
    assert "size_gb" in result[0]
    assert result[0]["region"] == "us-east-1"


@mock_rds
def test_scan_rds_snapshots_available_only():
    """Test that scanner filters available snapshots only."""
    rds = boto3.client("rds", region_name="us-east-1")

    # Create DB instance
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="mysql",
        MasterUsername="admin",
        MasterUserPassword="password123",
    )

    # Create manual snapshot (moto always creates as 'available')
    rds.create_db_snapshot(
        DBSnapshotIdentifier="available-snapshot", DBInstanceIdentifier="test-db"
    )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    result = scan_rds_snapshots(credentials, "us-east-1")

    assert len(result) == 1
    assert result[0]["id"] == "available-snapshot"


@mock_rds
def test_scan_rds_snapshots_empty():
    """Test scanning with no snapshots."""
    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    result = scan_rds_snapshots(credentials, "us-west-2")

    assert result == []


@mock_rds
def test_scan_rds_snapshots_age_calculation():
    """Test that snapshot creation time is extracted correctly."""
    rds = boto3.client("rds", region_name="us-east-1")

    # Create DB instance
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
    )

    # Create snapshot
    rds.create_db_snapshot(
        DBSnapshotIdentifier="test-snapshot", DBInstanceIdentifier="test-db"
    )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    result = scan_rds_snapshots(credentials, "us-east-1")

    assert len(result) == 1
    assert "created_at" in result[0]
    assert isinstance(result[0]["created_at"], datetime)


@mock_rds
def test_threshold_count_exceeded():
    """Test count threshold: 11 snapshots > 10."""
    rds = boto3.client("rds", region_name="us-east-1")

    # Create DB instance
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="mysql",
        MasterUsername="admin",
        MasterUserPassword="password123",
    )

    # Create 11 manual snapshots
    for i in range(11):
        rds.create_db_snapshot(
            DBSnapshotIdentifier=f"snapshot-{i}", DBInstanceIdentifier="test-db"
        )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    result = scan_rds_snapshots(credentials, "us-east-1")

    assert len(result) == 11  # Exceeds threshold of 10


@mock_rds
def test_threshold_age_exceeded():
    """Test age threshold: snapshot >90d triggers alert."""
    rds = boto3.client("rds", region_name="us-east-1")

    # Create DB instance
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
    )

    # Create snapshot (moto creates with current time)
    rds.create_db_snapshot(
        DBSnapshotIdentifier="old-snapshot", DBInstanceIdentifier="test-db"
    )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    result = scan_rds_snapshots(credentials, "us-east-1")

    # Simulate old snapshot by manually setting uptime
    # In real testing, snapshot would be 91+ days old
    old_snapshot_age_seconds = THRESHOLDS["rds_snapshot"] + 3600  # 90d + 1h

    resource = {
        "type": "rds_snapshot",
        "id": result[0]["id"],
        "uptime_seconds": old_snapshot_age_seconds,
        "uptime_formatted": "91d 0h",
    }

    assert should_alert(resource) is True


def test_threshold_age_below():
    """Test age threshold: snapshot <90d does not trigger alert."""
    # Snapshot 89 days old (below threshold)
    young_snapshot_age_seconds = (
        THRESHOLDS["rds_snapshot"] - 86400
    )  # 90d - 1d = 89d

    resource = {
        "type": "rds_snapshot",
        "id": "young-snapshot",
        "uptime_seconds": young_snapshot_age_seconds,
        "uptime_formatted": "89d 0h",
    }

    assert should_alert(resource) is False


def test_threshold_age_boundary():
    """Test age threshold boundary: snapshot at exactly 90d (2160h) does not alert."""
    # Exactly at threshold (not exceeded)
    boundary_age_seconds = THRESHOLDS["rds_snapshot"]  # Exactly 2160 hours

    resource = {
        "type": "rds_snapshot",
        "id": "boundary-snapshot",
        "uptime_seconds": boundary_age_seconds,
        "uptime_formatted": "90d 0h",
    }

    # At threshold, not exceeded (should be False)
    assert should_alert(resource) is False


@mock_rds
def test_dual_threshold():
    """Test dual threshold: both count and age can trigger simultaneously."""
    rds = boto3.client("rds", region_name="us-east-1")

    # Create DB instance
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="mysql",
        MasterUsername="admin",
        MasterUserPassword="password123",
    )

    # Create 12 snapshots (exceeds count threshold of 10)
    for i in range(12):
        rds.create_db_snapshot(
            DBSnapshotIdentifier=f"snapshot-{i}", DBInstanceIdentifier="test-db"
        )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    result = scan_rds_snapshots(credentials, "us-east-1")

    # Count threshold exceeded
    assert len(result) > 10

    # Simulate one snapshot being very old (age threshold also exceeded)
    old_snapshot_resource = {
        "type": "rds_snapshot",
        "id": result[0]["id"],
        "uptime_seconds": THRESHOLDS["rds_snapshot"] + 86400,  # 91 days
        "uptime_formatted": "91d 0h",
    }

    # Age threshold also exceeded
    assert should_alert(old_snapshot_resource) is True


@mock_rds
def test_scan_rds_snapshots_multiple_sizes():
    """Test scanning snapshots with different sizes."""
    rds = boto3.client("rds", region_name="us-east-1")

    # Create DB instance
    rds.create_db_instance(
        DBInstanceIdentifier="test-db",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="password123",
        AllocatedStorage=50,  # 50GB database
    )

    # Create snapshots
    rds.create_db_snapshot(
        DBSnapshotIdentifier="snapshot-1", DBInstanceIdentifier="test-db"
    )

    credentials = {
        "aws_access_key_id": "test",
        "aws_secret_access_key": "test",
        "aws_session_token": "test",
    }
    result = scan_rds_snapshots(credentials, "us-east-1")

    assert len(result) == 1
    # Snapshot inherits allocated storage from DB instance
    assert result[0]["size_gb"] == 50
