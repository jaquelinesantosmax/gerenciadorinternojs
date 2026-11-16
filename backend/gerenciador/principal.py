"""Monta o servidor. Para ligar: uvicorn gerenciador.principal:criar_app --factory"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api import admin, auth, espacos, itens, quadros, scrum
from .config import obter_config
from .erros import ErroDeRegra

METODOS_SEGUROS = {"GET", "HEAD", "OPTIONS"}
CABECALHO_ANTI_CSRF = "x-gerenciador"


def criar_app() -> FastAPI:
    cfg = obter_config()
    cfg.validar()
    dev = cfg.ambiente == "desenvolvimento"
    app = FastAPI(
        title="Gerenciador",
        docs_url="/api/docs" if dev else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if dev else None,
    )

    @app.middleware("http")
    async def protecao_csrf(request: Request, call_next):
        # Pedidos que mudam dados precisam de um cabeçalho que outro site não consegue enviar
        # sem autorização do navegador. Junto com o cookie SameSite=Lax, isso bloqueia CSRF.
        if (
            request.url.path.startswith("/api/")
            and request.method not in METODOS_SEGUROS
            and request.headers.get(CABECALHO_ANTI_CSRF) != "1"
        ):
            return JSONResponse({"detail": "Pedido recusado."}, status_code=403)
        return await call_next(request)

    @app.exception_handler(ErroDeRegra)
    async def erro_de_regra(_: Request, erro: ErroDeRegra):
        return JSONResponse({"detail": erro.mensagem}, status_code=erro.status)

    @app.get("/api/saude")
    def saude() -> dict[str, bool]:
        return {"ok": True}

    app.include_router(auth.rotas)
    app.include_router(admin.rotas)
    app.include_router(espacos.rotas)
    app.include_router(itens.rotas)
    app.include_router(quadros.rotas)
    app.include_router(scrum.rotas)
    return app
