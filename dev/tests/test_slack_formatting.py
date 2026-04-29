"""Unit tests for Slack message formatting and API functions."""

from unittest.mock import patch
from scanner.slack import (
    format_account_dm,
    format_monitoring_alert,
    format_scan_summary,
    should_alert,
    find_slack_user,
    open_dm_channel,
    send_message,
)


class TestThresholdLogic:
    """Test resource threshold detection."""

    def test_ec2_running_under_threshold(self):
        """EC2 running < 12h should not alert."""
        resource = {
            "type": "ec2",
            "state": "running",
            "uptime_seconds": 11 * 3600,  # 11 hours
        }
        assert not should_alert(resource)

    def test_ec2_running_over_threshold(self):
        """EC2 running > 12h should alert."""
        resource = {
            "type": "ec2",
            "state": "running",
            "uptime_seconds": 13 * 3600,  # 13 hours
        }
        assert should_alert(resource)

    def test_ec2_stopped_under_threshold(self):
        """EC2 stopped < 36h should not alert."""
        resource = {
            "type": "ec2",
            "state": "stopped",
            "uptime_seconds": 35 * 3600,  # 35 hours
        }
        assert not should_alert(resource)

    def test_ec2_stopped_over_threshold(self):
        """EC2 stopped > 36h should alert."""
        resource = {
            "type": "ec2",
            "state": "stopped",
            "uptime_seconds": 37 * 3600,  # 37 hours
        }
        assert should_alert(resource)

    def test_rds_under_threshold(self):
        """RDS < 24h should not alert."""
        resource = {
            "type": "rds",
            "state": "running",
            "uptime_seconds": 23 * 3600,  # 23 hours
        }
        assert not should_alert(resource)

    def test_rds_over_threshold(self):
        """RDS > 24h should alert."""
        resource = {
            "type": "rds",
            "state": "running",
            "uptime_seconds": 25 * 3600,  # 25 hours
        }
        assert should_alert(resource)

    def test_eks_under_threshold(self):
        """EKS < 24h should not alert."""
        resource = {
            "type": "eks",
            "state": "running",
            "uptime_seconds": 23 * 3600,  # 23 hours
        }
        assert not should_alert(resource)

    def test_eks_over_threshold(self):
        """EKS > 24h should alert."""
        resource = {
            "type": "eks",
            "state": "running",
            "uptime_seconds": 25 * 3600,  # 25 hours
        }
        assert should_alert(resource)

    def test_lightsail_under_threshold(self):
        """Lightsail < 168h (7 days) should not alert."""
        resource = {
            "type": "lightsail",
            "state": "running",
            "uptime_seconds": 167 * 3600,  # 167 hours (just under 7 days)
        }
        assert not should_alert(resource)

    def test_lightsail_over_threshold(self):
        """Lightsail > 168h (7 days) should alert."""
        resource = {
            "type": "lightsail",
            "state": "running",
            "uptime_seconds": 169 * 3600,  # 169 hours (over 7 days)
        }
        assert should_alert(resource)

    def test_lightsail_stopped_over_threshold(self):
        """Lightsail stopped > 168h should alert (stopped still incurs charges)."""
        resource = {
            "type": "lightsail",
            "state": "stopped",
            "uptime_seconds": 200 * 3600,  # 200 hours
        }
        assert should_alert(resource)


class TestShameMessages:
    """Test shame message conditions."""

    def test_shame_message_appears_once_for_long_running_ec2(self):
        """Shame emoji appears per instance > 12h, no per-section warning."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-1234",
                "instance_type": "t2.micro",
                "uptime_seconds": 13 * 3600,  # 13 hours
                "uptime_formatted": "13h",
            },
            {
                "type": "ec2",
                "state": "running",
                "id": "i-5678",
                "instance_type": "t2.small",
                "uptime_seconds": 15 * 3600,  # 15 hours
                "uptime_formatted": "15h",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # Emoji should appear per instance
        assert message_text.count("😱") == 2
        # Footer simplified
        assert message_text.count("Review resources to avoid charges") == 1

    def test_shame_message_not_for_short_running_ec2(self):
        """Shame emoji should NOT appear for EC2 < 12h."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-1234",
                "instance_type": "t2.micro",
                "uptime_seconds": 11 * 3600,  # 11 hours
                "uptime_formatted": "11h",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        assert "😱" not in message_text
        # Footer simplified
        assert "Review resources to avoid charges" in message_text

    def test_shame_message_not_for_stopped_ec2(self):
        """Shame emoji should NOT appear for stopped EC2."""
        resources = [
            {
                "type": "ec2",
                "state": "stopped",
                "id": "i-1234",
                "instance_type": "t2.micro",
                "uptime_seconds": 40 * 3600,  # 40 hours
                "uptime_formatted": "1d 16h",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        assert "😱" not in message_text
        # Footer simplified
        assert "Review resources to avoid charges" in message_text

    def test_monitoring_alert_shows_shame_indicator(self):
        """Monitoring alert should show ⚠️ for EC2 > 12h."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-1234",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 13 * 3600,
                "uptime_formatted": "13h 0m",
            }
        ]

        blocks = format_monitoring_alert(
            "TestAccount", "123456789012", "test@example.com", resources
        )
        message_text = str(blocks)

        assert "⚠️" in message_text


class TestAccountDMFormatting:
    """Test per-account DM message formatting."""

    def test_universal_header_present(self):
        """Universal header should appear first in all DMs."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-abc123",
                "name": "web-server",
                "instance_type": "t2.micro",
                "uptime_seconds": 13 * 3600,  # 13 hours
                "uptime_formatted": "13h",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        assert "AWS Resources Requiring Attention" in message_text
        # Removed redundant explanatory text
        assert "following resources have been active longer than recommended" not in message_text
        # Universal header should come first
        first_block = str(blocks[0])
        assert "AWS Resources Requiring Attention" in first_block

    def test_footer_present(self):
        """Concise footer should appear at end of all DMs."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-abc123",
                "name": "web-server",
                "instance_type": "t2.micro",
                "uptime_seconds": 13 * 3600,  # 13 hours
                "uptime_formatted": "13h",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # Removed emoji from footer
        assert "ℹ️" not in message_text
        # Simplified footer text
        assert "Review resources to avoid charges" in message_text
        # Footer should come last
        last_block = str(blocks[-1])
        assert "Review resources to avoid charges" in last_block

    def test_running_ec2_format(self):
        """Running EC2 instances should be formatted correctly."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-abc123",
                "name": "web-server",
                "instance_type": "t2.micro",
                "uptime_seconds": 7200,  # 2 hours
                "uptime_formatted": "2h",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # Removed emoji from header
        assert "AWS Resources Requiring Attention" in message_text
        assert "Running Instances:" in message_text
        assert "web-server" in message_text
        assert "t2.micro" in message_text
        assert "2h" in message_text

    def test_stopped_ec2_format(self):
        """Stopped EC2 instances should be formatted correctly."""
        resources = [
            {
                "type": "ec2",
                "state": "stopped",
                "id": "i-def456",
                "name": "backup-server",
                "instance_type": "t2.small",
                "uptime_seconds": 144000,  # 40 hours
                "uptime_formatted": "40h 0m",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        assert "🛑" in message_text
        assert "Stopped Instances:" in message_text
        assert "backup-server" in message_text
        assert "t2.small" in message_text
        assert "40h 0m" in message_text

    def test_rds_format(self):
        """RDS databases should be formatted correctly."""
        resources = [
            {
                "type": "rds",
                "state": "running",
                "id": "my-database",
                "instance_type": "db.t3.micro",
                "uptime_seconds": 93600,  # 26 hours
                "uptime_formatted": "26h 0m",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        assert "📊" in message_text
        assert "RDS Databases:" in message_text
        assert "my-database" in message_text
        assert "db.t3.micro" in message_text
        assert "26h 0m" in message_text

    def test_eks_format(self):
        """EKS clusters should be formatted correctly."""
        resources = [
            {
                "type": "eks",
                "state": "running",
                "id": "my-cluster",
                "name": "my-cluster",
                "version": "1.27",
                "instance_type": "",
                "uptime_seconds": 108900,  # 30h 15m
                "uptime_formatted": "30h 15m",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        assert "☸️" in message_text
        assert "EKS Clusters:" in message_text
        assert "my-cluster" in message_text
        assert "v1.27" in message_text
        assert "30h 15m" in message_text

    def test_mixed_resources_format(self):
        """Mixed resource types should be formatted correctly."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-111",
                "name": "web-server",
                "instance_type": "t2.micro",
                "uptime_seconds": 7200,
                "uptime_formatted": "2h",
            },
            {
                "type": "ec2",
                "state": "stopped",
                "id": "i-222",
                "name": "backup-server",
                "instance_type": "t2.small",
                "uptime_seconds": 144000,
                "uptime_formatted": "1d 16h",
            },
            {
                "type": "rds",
                "state": "running",
                "id": "db-1",
                "name": "db-1",
                "instance_type": "db.t3.micro",
                "uptime_seconds": 93600,
                "uptime_formatted": "1d 2h",
            },
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # Resource type emojis present
        assert "🛑" in message_text
        assert "📊" in message_text

        # All resources present
        assert "web-server" in message_text
        assert "backup-server" in message_text
        assert "db-1" in message_text


class TestMonitoringAlertFormatting:
    """Test monitoring channel alert formatting."""

    def test_monitoring_alert_basic_format(self):
        """Monitoring alert should have correct basic format."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 7200,
                "uptime_formatted": "2h 0m",
            }
        ]

        blocks = format_monitoring_alert(
            "AccountName", "123456789012", "user@example.com", resources
        )
        message_text = str(blocks)

        assert "🚨" in message_text
        assert "Active Resources Found" in message_text
        assert "User: AccountName" in message_text
        assert "Account: 123456789012" in message_text
        assert "Resources:" in message_text

    def test_monitoring_alert_resource_counts(self):
        """Monitoring alert should show detailed resource lines."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-1",
                "name": "web-1",
                "instance_type": "t2.micro",
                "uptime_seconds": 7200,
                "uptime_formatted": "2h 0m",
            },
            {
                "type": "ec2",
                "state": "running",
                "id": "i-2",
                "name": "web-2",
                "instance_type": "t2.micro",
                "uptime_seconds": 14400,
                "uptime_formatted": "4h 0m",
            },
            {
                "type": "ec2",
                "state": "stopped",
                "id": "i-3",
                "name": "backup",
                "instance_type": "t2.micro",
                "uptime_seconds": 144000,
                "uptime_formatted": "40h 0m",
            },
            {
                "type": "rds",
                "state": "running",
                "id": "db-1",
                "name": "db-1",
                "instance_type": "db.t3.micro",
                "uptime_seconds": 93600,
                "uptime_formatted": "26h 0m",
            },
        ]

        blocks = format_monitoring_alert(
            "AccountName", "123456789012", "user@example.com", resources
        )
        message_text = str(blocks)

        assert "• EC2: web-1 (t2.micro) - running" in message_text
        assert "• EC2: web-2 (t2.micro) - running" in message_text
        assert "• EC2: backup (t2.micro) - stopped" in message_text
        assert "• RDS: db-1 (db.t3.micro) - running" in message_text


class TestScanSummaryFormatting:
    """Test scan summary message formatting."""

    def test_scan_summary_format(self):
        """Scan summary should be formatted correctly."""
        blocks = format_scan_summary("dev", 15, 2, 42)
        message_text = str(blocks)

        # New compact format with warning emoji when failures exist
        assert "⚠️" in message_text  # Warning emoji (failed > 0)
        assert "System:" in message_text
        assert "Scanned 15 accounts" in message_text
        assert "2 failed" in message_text
        assert "42 total resources" in message_text


class TestSlackAPIFunctions:
    """Test Slack API integration functions."""

    @patch("scanner.slack.requests.get")
    def test_find_slack_user_success(self, mock_get):
        """find_slack_user should return user ID on success."""
        mock_get.return_value.json.return_value = {"ok": True, "user": {"id": "U12345"}}

        user_id = find_slack_user("test@example.com", "xoxb-token")
        assert user_id == "U12345"

        mock_get.assert_called_once_with(
            "https://slack.com/api/users.lookupByEmail",
            headers={"Authorization": "Bearer xoxb-token"},
            params={"email": "test@example.com"},
        )

    @patch("scanner.slack.requests.get")
    def test_find_slack_user_failure(self, mock_get):
        """find_slack_user should return None on failure."""
        from scanner.slack import _user_cache

        _user_cache.clear()

        mock_get.return_value.json.return_value = {"ok": False}

        user_id = find_slack_user("unknown@example.com", "xoxb-token")
        assert user_id is None

    @patch("scanner.slack.requests.get")
    def test_find_slack_user_caching(self, mock_get):
        """find_slack_user should cache user IDs."""
        from scanner.slack import _user_cache

        _user_cache.clear()

        mock_get.return_value.json.return_value = {"ok": True, "user": {"id": "U12345"}}

        # First call
        user_id1 = find_slack_user("test@example.com", "xoxb-token")
        assert user_id1 == "U12345"
        assert mock_get.call_count == 1

        # Second call should use cache
        user_id2 = find_slack_user("test@example.com", "xoxb-token")
        assert user_id2 == "U12345"
        assert mock_get.call_count == 1  # No additional call

    @patch("scanner.slack.requests.post")
    def test_open_dm_channel_success(self, mock_post):
        """open_dm_channel should return channel ID on success."""
        mock_post.return_value.json.return_value = {
            "ok": True,
            "channel": {"id": "C12345"},
        }

        channel_id = open_dm_channel("U12345", "xoxb-token")
        assert channel_id == "C12345"

        mock_post.assert_called_once_with(
            "https://slack.com/api/conversations.open",
            headers={"Authorization": "Bearer xoxb-token"},
            json={"users": "U12345"},
        )

    @patch("scanner.slack.requests.post")
    def test_open_dm_channel_failure(self, mock_post):
        """open_dm_channel should return None on failure."""
        mock_post.return_value.json.return_value = {"ok": False}

        channel_id = open_dm_channel("U12345", "xoxb-token")
        assert channel_id is None

    @patch("scanner.slack.requests.post")
    def test_send_message_success(self, mock_post):
        """send_message should return True on success."""
        mock_post.return_value.json.return_value = {"ok": True}
        mock_post.return_value.status_code = 200

        result = send_message(
            "C12345",
            [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}],
            "xoxb-token",
        )
        assert result is True

    @patch("scanner.slack.requests.post")
    def test_send_message_failure(self, mock_post):
        """send_message should return False on failure."""
        mock_post.return_value.json.return_value = {"ok": False}
        mock_post.return_value.status_code = 400

        result = send_message(
            "C12345",
            [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}],
            "xoxb-token",
        )
        assert result is False

    @patch("scanner.slack.requests.post")
    @patch("scanner.slack.time.sleep")
    def test_send_message_retry_on_429(self, mock_sleep, mock_post):
        """send_message should retry with backoff on 429 rate limit."""
        # First call returns 429, second succeeds
        mock_post.return_value.json.side_effect = [{"ok": False}, {"ok": True}]
        mock_post.return_value.status_code = 429
        mock_post.return_value.headers = {"Retry-After": "2"}

        send_message(
            "C12345",
            [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}],
            "xoxb-token",
        )

        assert mock_post.call_count == 2
        mock_sleep.assert_called_once_with(2)

    @patch("scanner.slack.requests.post")
    @patch("scanner.slack.time.sleep")
    def test_send_message_max_retries(self, mock_sleep, mock_post):
        """send_message should give up after max retries."""
        mock_post.return_value.json.return_value = {"ok": False}
        mock_post.return_value.status_code = 429
        mock_post.return_value.headers = {"Retry-After": "1"}

        blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "Test"}}]
        result = send_message("C12345", blocks, "xoxb-token", max_retries=3)

        assert result is False
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 3


class TestSendAlerts:
    """Test send_alerts orchestration function."""

    @patch("scanner.slack.send_message")
    @patch("scanner.slack.open_dm_channel")
    @patch("scanner.slack.find_slack_user")
    def test_send_alerts_success(self, mock_find_user, mock_open_dm, mock_send):
        """send_alerts should send DM and return monitoring data."""
        from scanner.slack import send_alerts

        mock_find_user.return_value = "U12345"
        mock_open_dm.return_value = "C12345"
        mock_send.return_value = True

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        result = send_alerts(
            "TestAccount",
            "123456789012",
            "test@example.com",
            resources,
            "xoxb-token",
            "C99999",
        )

        assert mock_find_user.call_count == 1
        assert mock_open_dm.call_count == 1
        assert mock_send.call_count == 1  # Only DM, no monitoring
        assert result["user_name"] == "TestAccount"
        assert result["account_id"] == "123456789012"
        assert len(result["high_cost_resources"]) == 1

    @patch("scanner.slack.find_slack_user")
    def test_send_alerts_user_not_found(self, mock_find_user, capsys):
        """send_alerts should warn when Slack user not found."""
        from scanner.slack import send_alerts

        mock_find_user.return_value = None

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        send_alerts(
            "TestAccount",
            "123456789012",
            "unknown@example.com",
            resources,
            "xoxb-token",
            "C99999",
        )

        captured = capsys.readouterr()
        assert "Warning: Slack user not found for unknown@example.com" in captured.out

    @patch("scanner.slack.open_dm_channel")
    @patch("scanner.slack.find_slack_user")
    def test_send_alerts_channel_open_fails(self, mock_find_user, mock_open_dm, capsys):
        """send_alerts should warn when DM channel cannot be opened."""
        from scanner.slack import send_alerts

        mock_find_user.return_value = "U12345"
        mock_open_dm.return_value = None

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        send_alerts(
            "TestAccount",
            "123456789012",
            "test@example.com",
            resources,
            "xoxb-token",
            "C99999",
        )

        captured = capsys.readouterr()
        assert "Warning: Could not open DM channel for test@example.com" in captured.out

    @patch("builtins.print")
    def test_send_alerts_dry_run(self, mock_print):
        """send_alerts should log messages in dry run mode and return monitoring data."""
        from scanner.slack import send_alerts

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        result = send_alerts(
            "TestAccount",
            "123456789012",
            "test@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=True,
        )

        # Verify dry run messages were printed (DRY_RUN skips DMs)
        calls = [str(call) for call in mock_print.call_args_list]
        assert any(
            "[DRY_RUN] Skipping DM for TestAccount" in str(call) for call in calls
        )
        # Verify monitoring data still returned
        assert result["user_name"] == "TestAccount"



class TestRevisedDryRunBehavior:
    """Test revised DRY_RUN and TEST_USER_EMAIL behavior."""

    @patch("scanner.slack.send_message")
    @patch("builtins.print")
    def test_dry_run_true_sends_monitoring_only(self, mock_print, mock_send):
        """DRY_RUN=true should skip DMs and return monitoring data."""
        from scanner.slack import send_alerts

        mock_send.return_value = True

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        result = send_alerts(
            "TestAccount",
            "123456789012",
            "test@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=True,
        )

        # Verify no messages sent (monitoring handled by lambda_handler)
        assert mock_send.call_count == 0

        # Verify DM was skipped with logging
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("[DRY_RUN] Skipping DM for TestAccount" in str(call) for call in calls)

        # Verify monitoring data returned
        assert result["user_name"] == "TestAccount"

    @patch("scanner.slack.send_message")
    @patch("scanner.slack.open_dm_channel")
    @patch("scanner.slack.find_slack_user")
    def test_dry_run_false_no_test_email_normal_production(
        self, mock_find_user, mock_open_dm, mock_send
    ):
        """DRY_RUN=false, TEST_USER_EMAIL=unset should send to real recipients."""
        from scanner.slack import send_alerts

        mock_find_user.return_value = "U12345"
        mock_open_dm.return_value = "C12345"
        mock_send.return_value = True

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        result = send_alerts(
            "TestAccount",
            "123456789012",
            "user@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=False,
            test_user_email=None,
        )

        # Verify DM sent to recipient's email
        mock_find_user.assert_called_with("user@example.com", "xoxb-token")
        assert mock_send.call_count == 1  # Only DM, monitoring handled by lambda_handler
        assert result["user_name"] == "TestAccount"

    @patch("scanner.slack.send_message")
    @patch("scanner.slack.open_dm_channel")
    @patch("scanner.slack.find_slack_user")
    def test_test_mode_redirects_to_test_user(
        self, mock_find_user, mock_open_dm, mock_send, capsys
    ):
        """DRY_RUN=false, TEST_USER_EMAIL=set should redirect DMs to test user."""
        from scanner.slack import send_alerts

        mock_find_user.return_value = "U_TEST"
        mock_open_dm.return_value = "C_TEST"
        mock_send.return_value = True

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        send_alerts(
            "TestAccount",
            "123456789012",
            "user@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=False,
            test_user_email="tester@acme.com",
        )

        # Verify test user was looked up instead of recipient
        mock_find_user.assert_called_once_with("tester@acme.com", "xoxb-token")

        # Verify test mode logging
        captured = capsys.readouterr()
        assert "[TEST_MODE] Sending DM for TestAccount to tester@acme.com" in captured.out

        # Verify DM sent (monitoring handled by lambda_handler)
        assert mock_send.call_count == 1

    @patch("scanner.slack.send_message")
    @patch("scanner.slack.open_dm_channel")
    @patch("scanner.slack.find_slack_user")
    def test_test_mode_adds_header_to_dm(self, mock_find_user, mock_open_dm, mock_send):
        """Test mode should add TEST MODE header to DM message."""
        from scanner.slack import send_alerts

        mock_find_user.return_value = "U_TEST"
        mock_open_dm.return_value = "C_TEST"
        mock_send.return_value = True

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        send_alerts(
            "TestAccount",
            "123456789012",
            "user@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=False,
            test_user_email="tester@acme.com",
        )

        # Get the blocks passed to send_message for DM
        dm_call = mock_send.call_args_list[0]
        dm_blocks = dm_call[0][1]

        # Verify test mode header is first block
        assert "TEST MODE" in str(dm_blocks[0])
        assert "TestAccount" in str(dm_blocks[0])
        assert "123456789012" in str(dm_blocks[0])

    @patch("scanner.slack.send_message")
    @patch("builtins.print")
    def test_dry_run_true_ignores_test_user_email(self, mock_print, mock_send):
        """DRY_RUN=true should ignore TEST_USER_EMAIL (DRY_RUN wins)."""
        from scanner.slack import send_alerts

        mock_send.return_value = True

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        send_alerts(
            "TestAccount",
            "123456789012",
            "user@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=True,
            test_user_email="tester@acme.com",
        )

        # Verify no messages sent (monitoring handled by lambda_handler)
        assert mock_send.call_count == 0

        # Verify DRY_RUN logging, not TEST_MODE logging
        calls = [str(call) for call in mock_print.call_args_list]
        assert any("[DRY_RUN] Skipping DM" in str(call) for call in calls)
        assert not any("[TEST_MODE]" in str(call) for call in calls)

    @patch("scanner.slack.send_message")
    @patch("scanner.slack.find_slack_user")
    def test_test_user_not_found_logs_error(self, mock_find_user, mock_send, capsys):
        """Test user not found should log error and continue with monitoring."""
        from scanner.slack import send_alerts

        mock_find_user.return_value = None  # Test user not found
        mock_send.return_value = True

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        send_alerts(
            "TestAccount",
            "123456789012",
            "user@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=False,
            test_user_email="invalid@acme.com",
        )

        # Verify error logged with test user indication
        captured = capsys.readouterr()
        assert "Warning: Slack user not found for invalid@acme.com (test user)" in captured.out

        # Verify no messages sent (monitoring handled by lambda_handler)
        assert mock_send.call_count == 0

    @patch("scanner.slack.send_message")
    @patch("scanner.slack.open_dm_channel")
    @patch("scanner.slack.find_slack_user")
    def test_multiple_accounts_test_mode(
        self, mock_find_user, mock_open_dm, mock_send
    ):
        """Test user should receive multiple DMs with correct headers for multiple accounts."""
        from scanner.slack import send_alerts

        mock_find_user.return_value = "U_TEST"
        mock_open_dm.return_value = "C_TEST"
        mock_send.return_value = True

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        # Simulate two accounts triggering alerts
        send_alerts(
            "Account1",
            "111111111111",
            "user1@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=False,
            test_user_email="tester@acme.com",
        )

        send_alerts(
            "Account2",
            "222222222222",
            "user2@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=False,
            test_user_email="tester@acme.com",
        )

        # Verify test user received two DMs (monitoring handled by lambda_handler)
        assert mock_send.call_count == 2

        # Verify headers contain correct account names
        dm_call1 = mock_send.call_args_list[0]
        dm_blocks1 = dm_call1[0][1]
        assert "Account1" in str(dm_blocks1[0])
        assert "111111111111" in str(dm_blocks1[0])

        dm_call2 = mock_send.call_args_list[1]  # Second DM is now at index 1
        dm_blocks2 = dm_call2[0][1]
        assert "Account2" in str(dm_blocks2[0])
        assert "222222222222" in str(dm_blocks2[0])

    @patch("scanner.slack.send_message")
    @patch("scanner.slack.open_dm_channel")
    @patch("scanner.slack.find_slack_user")
    def test_monitoring_channel_unchanged_in_test_mode(
        self, mock_find_user, mock_open_dm, mock_send
    ):
        """Monitoring data should reference original recipient in test mode."""
        from scanner.slack import send_alerts

        mock_find_user.return_value = "U_TEST"
        mock_open_dm.return_value = "C_TEST"
        mock_send.return_value = True

        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test-instance",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h 53m",
            }
        ]

        result = send_alerts(
            "TestAccount",
            "123456789012",
            "user@example.com",
            resources,
            "xoxb-token",
            "C99999",
            dry_run=False,
            test_user_email="tester@acme.com",
        )

        # Monitoring data should reference original recipient (not test user)
        assert result["user_name"] == "TestAccount"
        assert result["account_id"] == "123456789012"
        # Monitoring data built from original resources
        assert len(result["high_cost_resources"]) == 1


class TestStory310Formatting:
    """Test Slack Message Formatting Improvements."""

    def test_consolidated_blocks_reduces_count(self):
        """10 volumes should create far fewer blocks than old implementation."""
        resources = [
            {
                "type": "volume",
                "id": f"vol-{i:017x}",
                "size_gb": 8,
                "region": "ap-south-1",
                "uptime_seconds": 648000,  # ~7.5 days
                "uptime_formatted": "7d 12h",
            }
            for i in range(10)
        ]

        blocks = format_account_dm("TestAccount", resources)

        # Old: 1 header + 1 section title + 10 volume blocks + 1 footer = 13 blocks
        # New: 1 header + 1 consolidated volume block + 1 footer = 3 blocks
        # (Additional Resources section won't appear since volume_count not passed)
        assert len(blocks) <= 5, f"Expected ≤5 blocks, got {len(blocks)}"

    def test_all_resources_shown_with_full_ids(self):
        """All 10 volumes should be shown with full volume IDs."""
        resources = [
            {
                "type": "volume",
                "id": f"vol-0{i}abc123def456789",
                "size_gb": 2,
                "region": "ap-south-1",
                "uptime_seconds": 972000,  # ~11 days
                "uptime_formatted": "11d 6h",
            }
            for i in range(10)
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # Verify all 10 volumes present with full IDs
        for i in range(10):
            assert f"vol-0{i}abc123def456789" in message_text

    def test_duration_format_compact(self):
        """Duration should be in 'Xd Yh' format, not '270h 0m' format."""
        resources = [
            {
                "type": "volume",
                "id": "vol-abc123",
                "size_gb": 8,
                "region": "ap-south-1",
                "uptime_seconds": 972000,  # 270 hours = 11d 6h
                "uptime_formatted": "11d 6h",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # Verify compact format used
        assert "11d 6h" in message_text
        # Verify old format NOT used
        assert "270h" not in message_text

    def test_single_region_no_display(self):
        """Single-region account should not show region for each resource."""
        resources = [
            {
                "type": "volume",
                "id": "vol-111",
                "size_gb": 8,
                "region": "ap-south-1",
                "uptime_seconds": 648000,
                "uptime_formatted": "7d 12h",
            },
            {
                "type": "volume",
                "id": "vol-222",
                "size_gb": 2,
                "region": "ap-south-1",
                "uptime_seconds": 648000,
                "uptime_formatted": "7d 12h",
            },
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # All resources in same region, so region should NOT be shown
        assert "in ap-south-1" not in message_text

    def test_multi_region_displays_region(self):
        """Multi-region account should show region for each resource."""
        resources = [
            {
                "type": "volume",
                "id": "vol-111",
                "size_gb": 8,
                "region": "us-east-1",
                "uptime_seconds": 648000,
                "uptime_formatted": "7d 12h",
            },
            {
                "type": "volume",
                "id": "vol-222",
                "size_gb": 2,
                "region": "eu-west-1",
                "uptime_seconds": 648000,
                "uptime_formatted": "7d 12h",
            },
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # Multi-region account should show regions
        assert "in us-east-1" in message_text
        assert "in eu-west-1" in message_text

    def test_resource_counts_section_renamed(self):
        """'Additional Resources' section renamed to 'Resource Counts'."""
        resources = []

        blocks = format_account_dm(
            "TestAccount", resources, nat_count=3  # Triggers Resource Counts section
        )
        message_text = str(blocks)

        # Section renamed
        assert "Resource Counts:" in message_text
        # Old name should NOT appear
        assert "Additional Resources:" not in message_text

    def test_header_emoji_removed(self):
        """Header should not have ⚡ emoji."""
        resources = [
            {
                "type": "ec2",
                "state": "running",
                "id": "i-123",
                "name": "test",
                "instance_type": "t2.micro",
                "uptime_seconds": 50000,
                "uptime_formatted": "13h",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        first_block = str(blocks[0])

        # Header should not have emoji
        assert "⚡" not in first_block
        # But header text should still be there
        assert "AWS Resources Requiring Attention" in first_block

    def test_resource_type_emojis_preserved(self):
        """Resource-type emojis should be preserved (💾, 📊, ☸️, etc.)."""
        resources = [
            {
                "type": "volume",
                "id": "vol-123",
                "size_gb": 8,
                "region": "ap-south-1",
                "uptime_seconds": 648000,
                "uptime_formatted": "7d 12h",
            },
            {
                "type": "rds",
                "id": "db-1",
                "instance_type": "db.t3.micro",
                "uptime_seconds": 93600,
                "uptime_formatted": "1d 2h",
            },
            {
                "type": "ec2",
                "state": "stopped",
                "id": "i-123",
                "name": "test",
                "instance_type": "t2.micro",
                "uptime_seconds": 144000,
                "uptime_formatted": "1d 16h",
            },
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # Resource-type emojis should be preserved
        assert "💾" in message_text  # EBS Volumes
        assert "📊" in message_text  # RDS Databases
        assert "🛑" in message_text  # Stopped Instances

    def test_volume_format_idle_without_for(self):
        """Volume format should be 'idle Xd Yh' not 'idle for Xd Yh'."""
        resources = [
            {
                "type": "volume",
                "id": "vol-abc123",
                "size_gb": 8,
                "region": "ap-south-1",
                "uptime_seconds": 972000,
                "uptime_formatted": "11d 6h",
            }
        ]

        blocks = format_account_dm("TestAccount", resources)
        message_text = str(blocks)

        # Verify concise format (without "for")
        assert "idle 11d 6h" in message_text
        # Old format should NOT appear
        assert "idle for 11d 6h" not in message_text
