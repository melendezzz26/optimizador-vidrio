ROLES = {
    "ADMINISTRADOR": "Administrador",
    "ALMACENERO": "Almacenero",
    "OPERARIO": "Operario",
}


PERMISOS = {
    "GESTIONAR_USUARIOS": {
        "Administrador",
    },

    "CONSULTAR_TIPOS_VIDRIO": {
        "Administrador",
        "Almacenero",
        "Operario",
    },

    "GESTIONAR_TIPOS_VIDRIO": {
        "Administrador",
        "Almacenero",
    },

    "CONSULTAR_STOCK": {
        "Administrador",
        "Almacenero",
        "Operario",
    },

    "GESTIONAR_PLANCHAS": {
        "Administrador",
        "Almacenero",
    },

    "GESTIONAR_RETAZOS": {
        "Administrador",
        "Almacenero",
    },

    "GESTIONAR_PEDIDOS": {
        "Administrador",
        "Operario",
    },

    "GESTIONAR_PIEZAS": {
        "Administrador",
        "Operario",
    },

    "EJECUTAR_OPTIMIZACION": {
        "Administrador",
        "Operario",
    },

    "CONSULTAR_RESULTADOS": {
        "Administrador",
        "Almacenero",
        "Operario",
    },

    "CONFIGURAR_OPTIMIZADOR": {
        "Administrador",
    },
}


def tiene_permiso(rol: str, permiso: str) -> bool:
    """
    Verifica si un rol tiene permitido realizar una acción.
    """

    roles_permitidos = PERMISOS.get(permiso, set())

    return rol in roles_permitidos