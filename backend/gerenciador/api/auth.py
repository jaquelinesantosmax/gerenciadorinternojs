"""Rotas de entrada, saída e dados de quem está logado."""

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .. import sessoes
from ..auditoria import TipoEvento, registrar
from ..banco import obter_db
from ..config import obter_config
from ..identidade import IdentidadeExterna, entrar
from ..modelos import Usuario
from ..papeis import papeis_ativos, permissoes_de
from .deps import agente_do_pedido, apagar_cookie, gravar_cookie, ip_do_pedido, usuario_atual
from .esquemas import Eu, PedidoLoginTeste, Provedores

rotas = APIRouter(prefix="/api")


def montar_eu(db: Session, usuario: Usuario) -> Eu:
    papeis = papeis_ativos(db, usuario.id)
    return Eu(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        foto_url=usuario.foto_url,
        papeis=sorted(papeis, key=lambda p: p.value),
        permissoes=permissoes_de(papeis),
    )


@rotas.get("/auth/provedores", response_model=Provedores)
def provedores() -> Provedores:
    return Provedores(teste=obter_config().login_teste_habilitado, google=False)


@rotas.post("/auth/teste/entrar", response_model=Eu)
def entrar_teste(
    pedido: PedidoLoginTeste, request: Request, response: Response, db: Session = Depends(obter_db)
) -> Eu:
    """Login de teste, só para desenvolvimento: entra com qualquer e-mail de domínio autorizado,
    sem senha. Será trocado pelo login Google, que usa a mesma função entrar()."""
    if not obter_config().login_teste_habilitado:
        raise HTTPException(status_code=404, detail="Não encontrado.")
    identidade = IdentidadeExterna(email=pedido.email, nome=pedido.nome, provedor="teste")
    usuario, token = entrar(db, identidade, ip_do_pedido(request), agente_do_pedido(request))
    gravar_cookie(response, token)
    return montar_eu(db, usuario)


@rotas.post("/auth/sair", status_code=204)
def sair(request: Request, response: Response, db: Session = Depends(obter_db)) -> Response:
    sessao, _ = sessoes.validar(db, request.cookies.get(sessoes.NOME_COOKIE))
    if sessao is not None:
        sessoes.encerrar(db, sessao, "logout")
        registrar(db, TipoEvento.LOGOUT, ator_id=sessao.usuario_id, alvo_usuario_id=sessao.usuario_id,
                  ip=ip_do_pedido(request))
        db.commit()
    resposta = Response(status_code=204)
    apagar_cookie(resposta)
    return resposta


@rotas.get("/eu", response_model=Eu)
def eu(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> Eu:
    return montar_eu(db, usuario)
