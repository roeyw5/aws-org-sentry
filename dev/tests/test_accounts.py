"""Tests for account discovery from users mapping."""

from scanner.accounts import get_accounts_from_mapping


def test_get_accounts_from_mapping():
    """Test extracting accounts from users mapping."""
    users_mapping = {
        "dev-account":     {"id": "111111111111", "email": "dev@example.com"},
        "staging-account": {"id": "222222222222", "email": "staging@example.com"},
        "prod-account":    {"id": "333333333333", "email": "prod@example.com"},
    }

    accounts = get_accounts_from_mapping(users_mapping)

    assert len(accounts) == 3
    assert {"id": "111111111111", "name": "dev-account"} in accounts
    assert {"id": "222222222222", "name": "staging-account"} in accounts
    assert {"id": "333333333333", "name": "prod-account"} in accounts


def test_get_accounts_from_mapping_skips_missing_ids():
    """Test that accounts without IDs are skipped."""
    users_mapping = {
        "account-with-id":  {"id": "123456789012", "email": "with@example.com"},
        "account-no-id":    {"email": "without@example.com"},
        "account-null-id":  {"id": None, "email": "null@example.com"},
    }

    accounts = get_accounts_from_mapping(users_mapping)

    assert len(accounts) == 1
    assert accounts[0] == {"id": "123456789012", "name": "account-with-id"}


def test_get_accounts_from_mapping_empty():
    """Test empty users mapping."""
    accounts = get_accounts_from_mapping({})
    assert accounts == []


def test_get_accounts_from_mapping_returns_correct_structure():
    """Test that accounts have correct structure with id and name."""
    users_mapping = {
        "test-account": {"id": "123456789012", "email": "test@example.com"}
    }

    accounts = get_accounts_from_mapping(users_mapping)

    assert len(accounts) == 1
    assert "id" in accounts[0]
    assert "name" in accounts[0]
    assert accounts[0]["id"] == "123456789012"
    assert accounts[0]["name"] == "test-account"
