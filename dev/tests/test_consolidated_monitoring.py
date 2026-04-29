"""Unit tests for consolidated monitoring report."""

from scanner.slack import format_consolidated_monitoring_report, _get_local_timestamp


class TestConsolidatedMonitoringReport:
    """Test consolidated monitoring report formatting."""

    def test_empty_scan(self):
        """Empty scan should show success message."""
        blocks = format_consolidated_monitoring_report("dev", [])
        message_text = str(blocks)

        assert "✅" in message_text
        assert "dev Alert Report" in message_text
        assert "No active resources found" in message_text
        assert "UTC" in message_text or "Time" in message_text

    def test_single_user_high_cost_only(self):
        """Single user with only high-cost resources."""
        monitoring_data = [
            {
                "user_name": "User.A",
                "account_id": "123456789012",
                "high_cost_resources": [
                    {
                        "type": "ec2",
                        "id": "i-0a1b2c3d",
                        "instance_type": "t3.medium",
                        "state": "running",
                        "uptime_formatted": "48h",
                        "region": "ap-south-1",
                    }
                ],
                "low_cost_counts": {},
            }
        ]

        blocks = format_consolidated_monitoring_report("dev", monitoring_data)
        message_text = str(blocks)

        assert "🚨" in message_text
        assert "dev Alert Report" in message_text
        assert "1 user:" in message_text
        assert "User.A" in message_text
        assert "123456789012" in message_text
        assert "• EC2: i-0a1b2c3d (t3.medium) running 48h in ap-south-1" in message_text

    def test_single_user_low_cost_only(self):
        """Single user with only low-cost resources."""
        monitoring_data = [
            {
                "user_name": "User.B",
                "account_id": "234567890123",
                "high_cost_resources": [],
                "low_cost_counts": {"volumes": 10, "snapshots": 5},
            }
        ]

        blocks = format_consolidated_monitoring_report("staging", monitoring_data)
        message_text = str(blocks)

        assert "User.B" in message_text
        assert "234567890123" in message_text
        assert "• (10 volumes, 5 EBS snapshots)" in message_text

    def test_multiple_users_alphabetical_order(self):
        """Multiple users should be sorted alphabetically."""
        monitoring_data = [
            {
                "user_name": "User.C",
                "account_id": "111111111111",
                "high_cost_resources": [
                    {
                        "type": "ec2",
                        "id": "i-111",
                        "instance_type": "t2.micro",
                        "state": "running",
                        "uptime_formatted": "24h",
                    }
                ],
                "low_cost_counts": {},
            },
            {
                "user_name": "User.A",
                "account_id": "222222222222",
                "high_cost_resources": [
                    {
                        "type": "ec2",
                        "id": "i-222",
                        "instance_type": "t2.micro",
                        "state": "running",
                        "uptime_formatted": "24h",
                    }
                ],
                "low_cost_counts": {},
            },
        ]

        blocks = format_consolidated_monitoring_report("dev", monitoring_data)
        message_text = str(blocks)

        # Verify alphabetical order (User.A before User.C)
        user_a_pos = message_text.find("User.A")
        user_c_pos = message_text.find("User.C")
        assert user_a_pos < user_c_pos

    def test_resource_summary_aggregation(self):
        """Summary should aggregate resource counts across all users."""
        monitoring_data = [
            {
                "user_name": "User1",
                "account_id": "111111111111",
                "high_cost_resources": [
                    {
                        "type": "ec2",
                        "id": "i-1",
                        "instance_type": "t2.micro",
                        "state": "running",
                        "uptime_formatted": "24h",
                    },
                    {
                        "type": "rds",
                        "name": "db-1",
                        "instance_type": "db.t3.micro",
                        "state": "running",
                        "uptime_formatted": "48h",
                    },
                ],
                "low_cost_counts": {"volumes": 5},
            },
            {
                "user_name": "User2",
                "account_id": "222222222222",
                "high_cost_resources": [
                    {
                        "type": "ec2",
                        "id": "i-2",
                        "instance_type": "t2.small",
                        "state": "running",
                        "uptime_formatted": "12h",
                    }
                ],
                "low_cost_counts": {"volumes": 3, "snapshots": 2},
            },
        ]

        blocks = format_consolidated_monitoring_report("dev", monitoring_data)
        message_text = str(blocks)

        assert "2 users:" in message_text
        # 2 EC2, 1 RDS, 8 volumes total, 2 snapshots
        assert "2 EC2 running" in message_text
        assert "1 RDS" in message_text
        assert "8 volumes" in message_text
        assert "2 snapshots" in message_text

    def test_nat_and_elb_counts(self):
        """NAT and ELB should show as high-cost resources with counts."""
        monitoring_data = [
            {
                "user_name": "User1",
                "account_id": "111111111111",
                "high_cost_resources": [
                    {"type": "nat", "count": 2, "region": "ap-south-1"},
                    {"type": "elb", "count": 3, "region": "us-east-1"},
                ],
                "low_cost_counts": {},
            }
        ]

        blocks = format_consolidated_monitoring_report("dev", monitoring_data)
        message_text = str(blocks)

        assert "• NAT Gateways: 2 active in ap-south-1" in message_text
        assert "• Load Balancers: 3 active in us-east-1" in message_text
        assert "2 NAT" in message_text  # In summary
        assert "3 LBs" in message_text  # In summary

    def test_all_resource_types(self):
        """Test user with all resource types."""
        monitoring_data = [
            {
                "user_name": "PowerUser",
                "account_id": "999999999999",
                "high_cost_resources": [
                    {
                        "type": "ec2",
                        "id": "i-running",
                        "instance_type": "t3.large",
                        "state": "running",
                        "uptime_formatted": "24h",
                    },
                    {
                        "type": "rds",
                        "name": "prod-db",
                        "instance_type": "db.t3.small",
                        "state": "running",
                        "uptime_formatted": "72h",
                    },
                    {
                        "type": "eks",
                        "name": "cluster-1",
                        "version": "1.28",
                        "state": "running",
                        "uptime_formatted": "96h",
                    },
                    {
                        "type": "lightsail",
                        "name": "wordpress",
                        "bundle_id": "nano",
                        "state": "running",
                        "uptime_formatted": "168h",
                    },
                    {"type": "nat", "count": 2},
                    {"type": "elb", "count": 3},
                ],
                "low_cost_counts": {
                    "volumes": 10,
                    "snapshots": 5,
                    "rds_snapshots": 2,
                    "stopped_ec2": 3,
                    "eips": 4,
                    "vpc_endpoints": 2,
                },
            }
        ]

        blocks = format_consolidated_monitoring_report("dev", monitoring_data)
        message_text = str(blocks)

        # High-cost resources shown with details
        assert "• EC2: i-running (t3.large) running 24h" in message_text
        assert "• RDS: prod-db (db.t3.small) running 72h" in message_text
        assert "• EKS: cluster-1 (v1.28) running 96h" in message_text
        assert "• Lightsail: wordpress (nano) running 168h" in message_text
        assert "• NAT Gateways: 2 active" in message_text
        assert "• Load Balancers: 3 active" in message_text

        # Low-cost resources shown as counts
        assert "10 volumes" in message_text
        assert "5 EBS snapshots" in message_text
        assert "2 RDS snapshots" in message_text
        assert "3 stopped EC2s" in message_text
        assert "4 EIPs" in message_text
        assert "2 VPC endpoints" in message_text

    def test_zero_counts_omitted(self):
        """Zero counts should not appear in low-cost summary."""
        monitoring_data = [
            {
                "user_name": "User1",
                "account_id": "111111111111",
                "high_cost_resources": [
                    {
                        "type": "ec2",
                        "id": "i-123",
                        "instance_type": "t2.micro",
                        "state": "running",
                        "uptime_formatted": "24h",
                    }
                ],
                "low_cost_counts": {
                    "volumes": 5,
                    "snapshots": 0,  # Zero count
                    "eips": 0,  # Zero count
                },
            }
        ]

        blocks = format_consolidated_monitoring_report("dev", monitoring_data)
        message_text = str(blocks)

        # Only volumes should appear (non-zero)
        assert "5 volumes" in message_text
        # Zero counts should not appear
        assert "0 " not in message_text

    def test_local_timestamp_format(self):
        """Timestamp helper should return a formatted timezone-aware string."""
        timestamp = _get_local_timestamp()

        # Verify format: "YYYY-MM-DD HH:MM <tz>"
        assert len(timestamp.split("-")) == 3  # Year-Month-Day
        assert ":" in timestamp  # Hour:Minute separator
        # Default timezone is UTC if SCAN_TIMEZONE env var is not set
        assert "UTC" in timestamp or " " in timestamp

    def test_account_name_uppercase(self):
        """Account name should appear as provided (uppercase)."""
        monitoring_data = [
            {
                "user_name": "User1",
                "account_id": "111111111111",
                "high_cost_resources": [
                    {
                        "type": "ec2",
                        "id": "i-123",
                        "instance_type": "t2.micro",
                        "state": "running",
                        "uptime_formatted": "24h",
                    }
                ],
                "low_cost_counts": {},
            }
        ]

        blocks = format_consolidated_monitoring_report("staging", monitoring_data)
        message_text = str(blocks)

        assert "staging Alert Report" in message_text
