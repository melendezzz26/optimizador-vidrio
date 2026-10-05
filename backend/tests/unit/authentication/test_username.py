"""Formato del usuario de acceso (SPEC-HU-001, RN-02 y RN-03)."""
import pytest

from app.modules.authentication.domain.errors import InvalidUsernameError
from app.modules.authentication.domain.username import Username


def test_valid_username_is_kept():
    assert Username.parse("F71234567").value == "F71234567"


@pytest.mark.parametrize("raw", ["f71234567", "  F71234567  ", "\tf71234567\n"])
def test_username_is_normalized_to_uppercase_without_outer_spaces(raw):
    assert Username.parse(raw).value == "F71234567"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "71234567",          # solo el DNI, sin letra
        "F7123456",          # 7 dígitos
        "F712345678",        # 9 dígitos
        "FF1234567",         # dos letras
        "7F1234567",         # la letra no va primero
        "F7123 4567",        # espacio interior
        "F71234567X",        # carácter sobrante
        "Ñ71234567",         # letra fuera de A-Z
        "É71234567",
        "F７1234567",        # dígito que no es ASCII
        "admin",
        "persona@example.test",
        "' OR 1=1 --",
    ],
)
def test_invalid_username_is_rejected(raw):
    with pytest.raises(InvalidUsernameError):
        Username.parse(raw)


@pytest.mark.parametrize("raw", [None, 71234567, ["F71234567"]])
def test_non_text_username_is_rejected(raw):
    with pytest.raises(InvalidUsernameError):
        Username.parse(raw)


@pytest.mark.parametrize("value", ["f71234567", " F71234567", "admin"])
def test_username_cannot_be_built_without_normalizing(value):
    # Construirlo directamente no permite saltarse la validación.
    with pytest.raises(InvalidUsernameError):
        Username(value)


def test_invalid_username_error_explains_the_format():
    with pytest.raises(InvalidUsernameError, match="una letra seguida de 8 dígitos"):
        Username.parse("admin")
