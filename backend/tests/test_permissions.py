from app.core.permissions import tiene_permiso


def test_administrador_puede_gestionar_usuarios():
    assert tiene_permiso(
        "Administrador",
        "GESTIONAR_USUARIOS"
    ) is True


def test_operario_no_puede_gestionar_usuarios():
    assert tiene_permiso(
        "Operario",
        "GESTIONAR_USUARIOS"
    ) is False


def test_almacenero_puede_gestionar_planchas():
    assert tiene_permiso(
        "Almacenero",
        "GESTIONAR_PLANCHAS"
    ) is True


def test_operario_no_puede_gestionar_planchas():
    assert tiene_permiso(
        "Operario",
        "GESTIONAR_PLANCHAS"
    ) is False


def test_operario_puede_gestionar_pedidos():
    assert tiene_permiso(
        "Operario",
        "GESTIONAR_PEDIDOS"
    ) is True


def test_almacenero_no_puede_ejecutar_optimizacion():
    assert tiene_permiso(
        "Almacenero",
        "EJECUTAR_OPTIMIZACION"
    ) is False


def test_todos_pueden_consultar_resultados():
    assert tiene_permiso(
        "Administrador",
        "CONSULTAR_RESULTADOS"
    ) is True

    assert tiene_permiso(
        "Almacenero",
        "CONSULTAR_RESULTADOS"
    ) is True

    assert tiene_permiso(
        "Operario",
        "CONSULTAR_RESULTADOS"
    ) is True