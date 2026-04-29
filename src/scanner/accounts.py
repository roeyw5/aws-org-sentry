"""Account discovery from Parameter Store users mapping."""

from typing import List, Dict


def get_accounts_from_mapping(
    users_mapping: Dict[str, Dict[str, str]]
) -> List[Dict[str, str]]:
    """Get account list from users mapping.

    Args:
        users_mapping: Dictionary mapping account names to user data
                         Format: {"Account.Name": {"id": "123456789012",
                                  "email": "user@example.com"}}

    Returns:
        List of account dictionaries with 'id' and 'name' keys
        Example: [{'id': '123456789012', 'name': 'user-account'}]
    """
    accounts = []

    for account_name, user_data in users_mapping.items():
        account_id = user_data.get("id")
        if account_id:
            accounts.append({"id": account_id, "name": account_name})

    return accounts
