"""Hash y verificación de contraseñas (SPEC-HU-001, RN-04 y RN-05)."""
import pytest

from app.shared.security import MAX_PASSWORD_BYTES, hash_password, verify_password

PASSWORD = "clave-de-prueba-123"


def test_hash_is_not_the_plain_password():
    password_hash = hash_password(PASSWORD)
    assert password_hash != PASSWORD
    assert password_hash.startswith("$2")


def test_same_password_produces_different_hashes():
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_correct_password_is_verified():
    assert verify_password(PASSWORD, hash_password(PASSWORD))


def test_wrong_password_is_rejected():
    assert not verify_password("otra-clave", hash_password(PASSWORD))


def test_password_at_the_byte_limit_is_accepted():
    password = "a" * MAX_PASSWORD_BYTES
    assert verify_password(password, hash_password(password))


@pytest.mark.parametrize("password", ["", "a" * (MAX_PASSWORD_BYTES + 1), "ñ" * 37])
def test_hash_rejects_passwords_outside_the_byte_limit(password):
    with pytest.raises(ValueError):
        hash_password(password)


@pytest.mark.parametrize("password", ["", "a" * (MAX_PASSWORD_BYTES + 1), "ñ" * 37])
def test_verify_returns_false_for_passwords_outside_the_byte_limit(password):
    assert verify_password(password, hash_password(PASSWORD)) is False


@pytest.mark.parametrize("stored_hash", ["", "no-es-un-hash", "$2b$12$incompleto"])
def test_verify_returns_false_for_an_invalid_stored_hash(stored_hash):
    assert verify_password(PASSWORD, stored_hash) is False
