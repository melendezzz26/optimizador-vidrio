"""Tokens JWT de acceso (SPEC-HU-001, RN-09 a RN-11)."""
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest

from app.shared.security import create_access_token, decode_access_token
from app.shared.security.tokens import ALGORITHM, SECRET_KEY, TOKEN_MINUTES

BACKEND_DIR = Path(__file__).resolve().parents[3]


def encode(**changes):
    """Token firmado correctamente, con los datos que cada prueba altere."""
    payload = {
        "sub": "1",
        "username": "F71234567",
        "rol": "Administrador",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    payload.update(changes)
    payload = {key: value for key, value in payload.items() if value is not None}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def test_token_round_trip_keeps_identity_and_role():
    payload = decode_access_token(create_access_token(7, "F71234567", "Operario"))
    assert payload["sub"] == "7"
    assert payload["username"] == "F71234567"
    assert payload["rol"] == "Operario"


def test_token_expires_after_the_configured_minutes():
    payload = decode_access_token(create_access_token(7, "F71234567", "Operario"))
    expected = datetime.now(timezone.utc) + timedelta(minutes=TOKEN_MINUTES)
    assert abs(payload["exp"] - expected.timestamp()) < 5


def test_token_does_not_carry_personal_data():
    payload = decode_access_token(create_access_token(7, "F71234567", "Operario"))
    assert set(payload) == {"sub", "username", "rol", "exp"}


def test_expired_token_is_rejected():
    expired = encode(exp=datetime.now(timezone.utc) - timedelta(minutes=1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)


def test_token_signed_with_another_key_is_rejected():
    forged = jwt.encode(
        {"sub": "1", "username": "F71234567", "rol": "Administrador",
         "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "otra-clave-que-no-es-la-del-backend-0123456789",
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(forged)


@pytest.mark.parametrize("token", ["", "token.falso.123", "no-es-un-jwt"])
def test_malformed_token_is_rejected(token):
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(token)


@pytest.mark.parametrize("claim", ["sub", "username", "rol", "exp"])
def test_token_missing_a_required_claim_is_rejected(claim):
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(encode(**{claim: None}))


@pytest.mark.parametrize(
    "claim, value",
    [
        ("sub", "abc"),
        ("sub", "0"),
        ("sub", "-1"),
        ("sub", "99999999999"),
        ("username", ""),
        ("username", "   "),
        ("username", 123),
        ("rol", ""),
        ("rol", ["Administrador"]),
    ],
)
def test_token_with_an_invalid_claim_is_rejected(claim, value):
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(encode(**{claim: value}))


def import_tokens_module(environment):
    """Importa el módulo en un proceso aparte, sin leer el backend/.env local."""
    script = (
        "from unittest.mock import patch\n"
        "with patch('dotenv.load_dotenv', return_value=False):\n"
        "    import app.shared.security.tokens\n"
    )
    return subprocess.run(
        [sys.executable, "-B", "-c", script],
        cwd=BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_backend_does_not_start_without_secret_key():
    environment = {key: value for key, value in os.environ.items() if key != "SECRET_KEY"}
    result = import_tokens_module(environment)
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr


def test_backend_does_not_start_with_a_blank_secret_key():
    result = import_tokens_module({**os.environ, "SECRET_KEY": "   "})
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr


@pytest.mark.parametrize("minutes", ["0", "-5"])
def test_backend_does_not_start_with_a_non_positive_token_lifetime(minutes):
    result = import_tokens_module({**os.environ, "TOKEN_MINUTOS": minutes})
    assert result.returncode != 0
    assert "TOKEN_MINUTOS" in result.stderr


def test_backend_starts_with_a_valid_configuration():
    assert import_tokens_module(dict(os.environ)).returncode == 0
