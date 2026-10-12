import pytest

from app.modules.inventory.domain.exceptions import InventoryValidationError
from app.modules.inventory.domain.writeoff import BajaManual, TipoEventoBajaManual


@pytest.mark.parametrize("event", list(TipoEventoBajaManual))
def test_manual_writeoff_accepts_only_approved_categories(event):
    result = BajaManual(tipo_evento=event, motivo="  Material roto  ")

    assert result.tipo_evento is event
    assert result.motivo == "Material roto"
    assert result.observacion is None


@pytest.mark.parametrize("event", ["CONSUMO_OPTIMIZACION", "OTRO", ""])
def test_manual_writeoff_rejects_reserved_and_unknown_categories(event):
    with pytest.raises(InventoryValidationError, match="tipo_evento"):
        BajaManual(tipo_evento=event, motivo="Retiro")


@pytest.mark.parametrize("reason", ["", "   ", None, 7])
def test_manual_writeoff_requires_nonblank_text_reason(reason):
    with pytest.raises(InventoryValidationError, match="motivo"):
        BajaManual(tipo_evento=TipoEventoBajaManual.BAJA_RETIRO, motivo=reason)


def test_manual_writeoff_keeps_optional_observation_as_entered():
    result = BajaManual(
        tipo_evento=TipoEventoBajaManual.BAJA_MERMA,
        motivo="Merma",
        observacion="  Detalle complementario  ",
    )

    assert result.observacion == "  Detalle complementario  "


def test_manual_writeoff_rejects_non_text_observation():
    with pytest.raises(InventoryValidationError, match="observacion"):
        BajaManual(
            tipo_evento=TipoEventoBajaManual.BAJA_ROTURA,
            motivo="Rotura",
            observacion=12,
        )
