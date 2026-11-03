"""HU-018: caso de uso de previsualización (SPEC-HU-018 §6.3 y §7)."""
import pytest

from app.modules.orders.application.bulk_import import ImportFileError, PreviewImportUseCase


def preview(*texts, archivo="piezas.csv"):
    return PreviewImportUseCase().execute(archivo, list(enumerate(texts, start=1)))


def test_summary_counts_valid_and_observed_rows():
    result = preview("tipo,cantidad,medidas", "R,3,800,600", "C,0,150", "C,2,150")
    assert result["archivo"] == "piezas.csv"
    assert result["resumen"] == {"total": 3, "validas": 2, "observadas": 1}
    assert [(row["fila"], row["estado"]) for row in result["filas"]] == [(2, "VALIDO"), (3, "OBSERVADO"), (4, "VALIDO")]


def test_rows_use_the_response_fields():
    row = preview("R,3,800,600")["filas"][0]
    assert row == {"fila": 1, "texto": "R,3,800,600", "estado": "VALIDO", "tipo_forma": "RECTANGULO",
                   "cantidad": 3, "medidas": {"width_mm": 800, "height_mm": 600}, "causas": []}


@pytest.mark.parametrize("texts", [(), ("",), (" ", ",,"), ("tipo,cantidad,medidas",)])
def test_file_without_pieces_is_rejected(texts):
    with pytest.raises(ImportFileError, match="no contiene piezas") as error:
        preview(*texts)
    assert error.value.status_code == 422


def test_exactly_500_rows_are_accepted_and_501_are_rejected():
    assert preview(*["C,1,10"] * 500)["resumen"]["total"] == 500
    with pytest.raises(ImportFileError, match="máximo de 500 filas"):
        preview(*["C,1,10"] * 501)


def test_empty_rows_do_not_count_towards_the_limit():
    assert preview(*(["C,1,10", ""] * 500))["resumen"]["total"] == 500


def test_very_long_row_is_rejected():
    with pytest.raises(ImportFileError, match="4000 caracteres"):
        preview("P,1," + "{10,10}," * 600)
        

def test_revalidation_never_drops_a_corrected_row_as_header():
    result = PreviewImportUseCase().execute("piezas.csv", [(4, "circulo"), (5, "C,1,10")], skip_header=False)
    assert [(row["fila"], row["estado"]) for row in result["filas"]] == [(4, "OBSERVADO"), (5, "VALIDO")]
    assert "Tipo de pieza desconocido" in result["filas"][0]["causas"]
    
    
def test_revalidation_never_drops_an_emptied_row():
    result = PreviewImportUseCase().execute("piezas.csv", [(4, ""), (5, "C,1,10")], skip_header=False)
    assert result["resumen"] == {"total": 2, "validas": 1, "observadas": 1}
    assert result["filas"][0]["fila"] == 4