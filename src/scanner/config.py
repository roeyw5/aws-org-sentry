"""Configuration loading from AWS Parameter Store."""

import boto3
import json
from typing import Dict, List
from botocore.exceptions import ClientError


class Config:
    """Configuration container for scanner settings."""

    def __init__(self, account_name: str):
        """Initialize configuration from Parameter Store.

        Args:
            account_name: Account identifier (e.g., 'dev', 'staging')

        Raises:
            Exception: If any required parameter cannot be loaded
        """
        self.account_name = account_name
        self._load_from_parameter_store()

    def _load_from_parameter_store(self) -> None:
        """Load all configuration parameters from Parameter Store.

        Raises:
            Exception: If any parameter is missing or invalid
        """
        ssm = boto3.client("ssm")
        base_path = f"/org-scanner/{self.account_name}"

        try:
            # Load Slack token (SecureString)
            self.slack_token = ssm.get_parameter(
                Name=f"{base_path}/slack-token", WithDecryption=True
            )["Parameter"]["Value"]

            # Load monitoring channel ID (String)
            self.monitoring_channel = ssm.get_parameter(
                Name=f"{base_path}/monitoring-channel"
            )["Parameter"]["Value"]

            # Load users mapping (SecureString, JSON)
            # Format: {"Account.Name": {"id": "123456789012", "email": "user@example.com"}}
            users_json = ssm.get_parameter(
                Name=f"{base_path}/users-mapping", WithDecryption=True
            )["Parameter"]["Value"]
            users_data = json.loads(users_json)

            # Support both old format (string emails) and new format (dict with id+email)
            self.users_mapping: Dict[str, Dict[str, str]] = {}
            for account_name, value in users_data.items():
                if isinstance(value, str):
                    # Old format: just email string
                    self.users_mapping[account_name] = {"email": value, "id": None}
                else:
                    # New format: dict with id and email
                    self.users_mapping[account_name] = value

            # Load OU ID (String)
            self.ou_id = ssm.get_parameter(Name=f"{base_path}/ou-id")["Parameter"][
                "Value"
            ]

            # Load regions (String, comma-separated)
            regions_str = ssm.get_parameter(Name=f"{base_path}/regions")["Parameter"][
                "Value"
            ]
            self.regions: List[str] = [r.strip() for r in regions_str.split(",")]

            # Load scan toggles (String, JSON)
            toggles_json = ssm.get_parameter(Name=f"{base_path}/scan-toggles")[
                "Parameter"
            ]["Value"]
            self.scan_toggles: Dict[str, bool] = json.loads(toggles_json)

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "ParameterNotFound":
                raise ValueError(
                    f"Required parameter not found in {base_path}. "
                    "Ensure all parameters are created in Parameter Store."
                ) from e
            raise Exception(f"AWS SSM error loading configuration: {e}") from e
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in parameter {base_path}: {e}") from e
        except Exception as e:
            raise Exception(f"Failed to load configuration: {e}") from e


_config_cache: Dict[str, Config] = {}


def get_config(account_name: str) -> Config:
    """Get cached configuration or load from Parameter Store.

    Args:
        account_name: Account identifier

    Returns:
        Config object with all settings loaded
    """
    if account_name not in _config_cache:
        _config_cache[account_name] = Config(account_name)
    return _config_cache[account_name]
