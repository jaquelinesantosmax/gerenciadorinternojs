"""Dependências comuns das rotas: usuário logado, IP e cookie de sessão."""

from ipaddress import ip_address

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .. import sessoes
from ..banco import obter_db
from ..config import obter_config
from ..modelos import Usuario


def ip_do_pedido(request: Request) -> str | None:
    """IP de quem fez o pedido. O cabeçalho X-Forwarded-For só é aceito quando o pedido vem
    da própria máquina (o servidor das telas repassando o pedido), para não ser falsificado."""
    direto = request.client.host if request.client else None
    encaminhado = request.headers.get("x-forwarded-for")
    if direto and encaminhado:
        try:
            if ip_address(direto).is_loopback:
                return encaminhado.split(",")[0].strip()[:64]
        except ValueError:
            pass
    return direto


def agente_do_pedido(request: Request) -> str | None:
    return request.headers.get("user-agent")


def gravar_cookie(response: Response, token: str) -> None:
    cfg = obter_config()
    response.set_cookie(
        sessoes.NOME_COOKIE,
        token,
        max_age=int(sessoes.duracao().total_seconds()),
        httponly=True,
        secure=cfg.cookie_seguro,
        samesite="lax",
        path="/",
    )


def apagar_cookie(response: Response) -> None:
    response.delete_cookie(sessoes.NOME_COOKIE, path="/")


def usuario_atual(request: Request, response: Response, db: Session = Depends(obter_db)) -> Usuario:
    token = request.cookies.get(sessoes.NOME_COOKIE)
    sessao, renovada = sessoes.validar(db, token)
    if sessao is None:
        raise HTTPException(status_code=401, detail="Sua sessão terminou. Entre de novo.")
    if renovada:
        db.commit()
        gravar_cookie(response, token)  # type: ignore[arg-type]
    request.state.sessao = sessao
    return sessao.usuario
