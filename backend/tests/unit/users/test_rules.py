"""Reglas de los datos de un usuario (SPEC-HU-003, sección 4, RN-02 y RN-03)."""
import pytest

from app.modules.authentication.domain.username import Username
from app.modules.users.domain.errors import InvalidUserDataError
from app.modules.users.domain.rules import (
    generate_access_username,
    normalize_name,
    validate_dni,
    validate_password,
)


@pytest.mark.parametrize(
    "first_names, expected",
    [
        ("Fabricio", "F71234567"),
        ("fabricio", "F71234567"),
        ("Álvaro", "A71234567"),
        ("Ñusta", "N71234567"),
        ("  María   José ", "M71234567"),
        ("Óscar Iván", "O71234567"),
    ],
)
def test_username_is_the_uppercase_initial_without_accent_plus_the_dni(first_names, expected):
    assert generate_access_username(first_names, "71234567") == expected


def test_generated_username_is_accepted_by_the_login_rule():
    # El login (SPEC-HU-001) exige una letra mayúscula y 8 dígitos.
    generated = generate_access_username("Álvaro", "71234567")
    assert Username(generated).value == generated


@pytest.mark.parametrize("first_names", ["1uis", "-Ana", "¿Luis", "", "   "])
def test_username_requires_a_name_that_starts_with_a_letter(first_names):
    with pytest.raises(InvalidUserDataError):
        generate_access_username(first_names, "71234567")


@pytest.mark.parametrize("dni", ["1234567", "123456789", "7123456A", "", " 71234567", "７１２３４５６７", None, 71234567])
def test_dni_must_have_exactly_eight_ascii_digits(dni):
    with pytest.raises(InvalidUserDataError):
        validate_dni(dni)


def test_valid_dni_is_returned_unchanged():
    assert validate_dni("07123456") == "07123456"


def test_name_is_trimmed_and_inner_spaces_are_collapsed():
    assert normalize_name("  Ana   María  ", "nombres") == "Ana María"


@pytest.mark.parametrize("value", ["", "    ", None, "a" * 101])
def test_name_must_have_between_1_and_100_characters(value):
    with pytest.raises(InvalidUserDataError):
        normalize_name(value, "nombres")


def test_name_of_100_characters_is_accepted():
    assert normalize_name("a" * 100, "apellidos") == "a" * 100


@pytest.mark.parametrize("password", ["", "1234567", None, "a" * 73, "ñ" * 37])
def test_password_must_have_8_characters_and_at_most_72_bytes(password):
    with pytest.raises(InvalidUserDataError):
        validate_password(password)


@pytest.mark.parametrize("password", ["12345678", "a" * 72, "ñ" * 36])
def test_password_within_the_limits_is_accepted(password):
    assert validate_password(password) == password
