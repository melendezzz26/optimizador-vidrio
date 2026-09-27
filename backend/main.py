from fastapi import FastAPI

app = FastAPI(
    title="Optimizador de Corte de Vidrio",
    version="1.0.0"
)


@app.get("/")
def inicio():
    return {
        "mensaje": "Backend del optimizador de vidrio funcionando"
    }