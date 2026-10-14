"""
Unit tests for the shared password policy (app/services/passwords.py).
"""

import pytest

from app.services.passwords import MIN_PASSWORD_LENGTH, is_common_password, password_problem


def test_short_passwords_are_refused():
    assert "at least 12 characters" in password_problem("x" * (MIN_PASSWORD_LENGTH - 1))


@pytest.mark.parametrize("pw", ["password1234", "qwertyuiop123", "123456789012", "iloveyou1234"])
def test_common_passwords_are_refused(pw):
    assert "commonly used" in password_problem(pw)


def test_the_check_ignores_case_and_surrounding_spaces():
    # Capitalising a breached password does not make it a new one.
    assert is_common_password("Password1234")
    assert is_common_password("  PASSWORD1234 ")


def test_a_long_uncommon_passphrase_is_accepted():
    assert password_problem("lambanog-tricycle-sampaguita-77") is None


def test_the_bundled_list_has_no_entry_the_length_rule_would_already_reject():
    from app.services.passwords import _common_passwords

    words = _common_passwords()
    assert len(words) > 10_000
    assert min(len(w) for w in words) >= MIN_PASSWORD_LENGTH
