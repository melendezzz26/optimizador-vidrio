import pytest
from pydantic import ValidationError

from app.modules.inventory.domain.writeoff import TipoEventoBajaManual
from app.modules.inventory.presentation.schemas import BajaManualRequest


@pytest.mark.parametrize("event", list(TipoEventoBajaManual))
def test_baja_request_accepts_approved_manual_event(event):
    payload = BajaManualRequest(tipo_evento=event, motivo="Retiro por daño")

    assert payload.tipo_evento is event
    assert payload.motivo == "Retiro por daño"
    assert payload.observacion is None


@pytest.mark.parametrize("payload", [
    {"tipo_evento": "CONSUMO_OPTIMIZACION", "motivo": "Consumo"},
    {"tipo_evento": "BAJA_RETIRO", "motivo": "   "},
    {"tipo_evento": "BAJA_RETIRO", "motivo": "Retiro", "id_usuario": 1},
    {"tipo_evento": "BAJA_RETIRO", "motivo": "Retiro", "fecha": "2026-10-09T10:00:00Z"},
    {"tipo_evento": "BAJA_RETIRO", "motivo": "Retiro", "id_optimizacion": 1},
])
def test_baja_request_rejects_reserved_empty_and_server_owned_fields(payload):
    with pytest.raises(ValidationError):
        BajaManualRequest.model_validate(payload)
