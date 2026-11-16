"""Rotas da administração da plataforma: usuários, papéis, Gestores, auditoria e domínios."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import dominios, papeis, usuarios
from ..banco import obter_db
from ..modelos import ConcessaoPapel, EventoAuditoria, Papel, Usuario
from .deps import ip_do_pedido, usuario_atual
from .esquemas import (
    DominioItem,
    EventoItem,
    GestorItem,
    PaginaEventos,
    PedidoDominio,
    PedidoPapel,
    PessoaResumo,
    UsuarioAdmin,
)

rotas = APIRouter(prefix="/api/admin")


def _papeis_por_usuario(db: Session) -> dict[uuid.UUID, list[Papel]]:
    resultado: dict[uuid.UUID, list[Papel]] = {}
    linhas = db.execute(
        select(ConcessaoPapel.usuario_id, ConcessaoPapel.papel).where(ConcessaoPapel.revogado_em.is_(None))
    )
    for usuario_id, papel in linhas:
        resultado.setdefault(usuario_id, []).append(Papel(papel))
    return resultado


@rotas.get("/usuarios", response_model=list[UsuarioAdmin])
def listar_usuarios(
    busca: str | None = Query(default=None, max_length=200),
    ator: Usuario = Depends(usuario_atual),
    db: Session = Depends(obter_db),
) -> list[UsuarioAdmin]:
    lista = usuarios.listar(db, ator, busca)
    mapa = _papeis_por_usuario(db)
    return [
        UsuarioAdmin(
            id=u.id, nome=u.nome, email=u.email, foto_url=u.foto_url, ativo=u.ativo,
            papeis=sorted(mapa.get(u.id, []), key=lambda p: p.value),
            criado_em=u.criado_em, ultimo_acesso_em=u.ultimo_acesso_em, desativado_em=u.desativado_em,
        )
        for u in lista
    ]


@rotas.post("/usuarios/{usuario_id}/papeis", status_code=204)
def conceder_papel(
    usuario_id: uuid.UUID, pedido: PedidoPapel, request: Request,
    ator: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    papeis.conceder(db, ator, usuario_id, pedido.papel, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.delete("/usuarios/{usuario_id}/papeis/{papel}", status_code=204)
def revogar_papel(
    usuario_id: uuid.UUID, papel: Papel, request: Request,
    ator: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    papeis.revogar(db, ator, usuario_id, papel, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.post("/usuarios/{usuario_id}/desativar", status_code=204)
def desativar_usuario(
    usuario_id: uuid.UUID, request: Request,
    ator: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    usuarios.desativar(db, ator, usuario_id, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.post("/usuarios/{usuario_id}/reativar", status_code=204)
def reativar_usuario(
    usuario_id: uuid.UUID, request: Request,
    ator: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    usuarios.reativar(db, ator, usuario_id, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.get("/gestores", response_model=list[GestorItem])
def listar_gestores(ator: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[GestorItem]:
    papeis.exigir(db, ator, "ver_usuarios")
    return [
        GestorItem(usuario=PessoaResumo.de(g.usuario), concedido_por=PessoaResumo.de(g.concedido_por),
                   concedido_em=g.concedido_em)
        for g in papeis.listar_gestores(db)
    ]


@rotas.get("/auditoria", response_model=PaginaEventos)
def listar_auditoria(
    tipo: str | None = Query(default=None, max_length=48),
    usuario_id: uuid.UUID | None = None,
    desde: datetime | None = None,
    ate: datetime | None = None,
    antes_de: int | None = Query(default=None, description="Para paginar: id do último evento já mostrado"),
    limite: int = Query(default=50, ge=1, le=200),
    ator: Usuario = Depends(usuario_atual),
    db: Session = Depends(obter_db),
) -> PaginaEventos:
    """Eventos do mais recente para o mais antigo."""
    papeis.exigir(db, ator, "ver_auditoria")
    consulta = select(EventoAuditoria).order_by(EventoAuditoria.id.desc()).limit(limite + 1)
    if tipo:
        consulta = consulta.where(EventoAuditoria.tipo == tipo)
    if usuario_id:
        consulta = consulta.where(
            (EventoAuditoria.ator_id == usuario_id) | (EventoAuditoria.alvo_usuario_id == usuario_id)
        )
    if desde:
        consulta = consulta.where(EventoAuditoria.ocorrido_em >= desde)
    if ate:
        consulta = consulta.where(EventoAuditoria.ocorrido_em <= ate)
    if antes_de:
        consulta = consulta.where(EventoAuditoria.id < antes_de)
    linhas = list(db.scalars(consulta).unique())
    pagina = linhas[:limite]
    return PaginaEventos(
        eventos=[
            EventoItem(id=e.id, ocorrido_em=e.ocorrido_em, tipo=e.tipo, ator=PessoaResumo.de(e.ator),
                       alvo=PessoaResumo.de(e.alvo), detalhes=e.detalhes or {}, ip=e.ip)
            for e in pagina
        ],
        proximo=pagina[-1].id if len(linhas) > limite else None,
    )


@rotas.get("/dominios", response_model=list[DominioItem])
def listar_dominios(ator: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[DominioItem]:
    papeis.exigir(db, ator, "configurar_dominios")
    itens = []
    for d in dominios.listar(db):
        autor = db.get(Usuario, d.adicionado_por_id) if d.adicionado_por_id else None
        itens.append(
            DominioItem(dominio=d.dominio, adicionado_por=PessoaResumo.de(autor), adicionado_em=d.adicionado_em)
        )
    return itens


@rotas.post("/dominios", status_code=204)
def adicionar_dominio(
    pedido: PedidoDominio, request: Request,
    ator: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    dominios.adicionar(db, ator, pedido.dominio, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.delete("/dominios/{dominio}", status_code=204)
def remover_dominio(
    dominio: str, request: Request,
    ator: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    dominios.remover(db, ator, dominio, ip_do_pedido(request))
    return Response(status_code=204)
