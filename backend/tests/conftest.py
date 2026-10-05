"""Configuración común de las pruebas: nunca usan la base ni la clave reales."""
import os
import secrets

# Se fijan antes de importar la aplicación. Como load_dotenv() no reemplaza
# variables ya definidas, ninguna prueba llega a leer el backend/.env local.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = secrets.token_urlsafe(48)
os.environ["TOKEN_MINUTOS"] = "480"
