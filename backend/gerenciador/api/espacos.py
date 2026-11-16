"""Rotas de espaços, membros, painéis, tipos, status, origens e Times provisórios."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from .. import espacos as svc
from .. import times
from ..banco import obter_db
from ..modelos import Usuario
from ..modelos_espacos import Espaco
from .deps import ip_do_pedido, usuario_atual
from .esquemas import PessoaResumo

rotas = APIRouter(prefix="/api")


# --- Formatos ---------------------------------------------------------------------------------

class Opcao(BaseModel):
    id: uuid.UUID
    nome: str


class EspacoResumo(BaseModel):
    id: uuid.UUID
    sigla: str
    nome: str
    tipo: str
    modelo: str | None
    meu_papel: str
    # Painéis aparecem em cascata abaixo do nome do espaço no menu (decisão de 16/11).
    paineis: list[Opcao] = []


class TipoSaida(BaseModel):
    id: uuid.UUID
    nome: str
    nivel: str
    padrao: bool


class StatusSaida(BaseModel):
    id: uuid.UUID
    nome: str
    categoria: str


class EspacoDetalhe(EspacoResumo):
    descricao: str | None
    criado_em: datetime
    permissoes: dict[str, bool]
    paineis: list[Opcao]
    tipos: list[TipoSaida]
    status: list[StatusSaida]
    origens: list[Opcao]


class PedidoEspaco(BaseModel):
    tipo: str
    nome: str = Field(max_length=200)
    sigla: str = Field(max_length=20)
    modelo: str | None = None


class PedidoEditarEspaco(BaseModel):
    nome: str | None = Field(default=None, max_length=200)
    descricao: str | None = Field(default=None, max_length=5000)


class MembroSaida(BaseModel):
    usuario: PessoaResumo
    papel: str
    adicionado_em: datetime


class PedidoMembro(BaseModel):
    usuario_id: uuid.UUID
    papel: str


class PedidoPapelMembro(BaseModel):
    papel: str


class PedidoNome(BaseModel):
    nome: str = Field(max_length=200)


class TimeSaida(BaseModel):
    id: uuid.UUID
    nome: str
    ativo: bool


class PedidoTime(BaseModel):
    nome: str | None = Field(default=None, max_length=200)
    ativo: bool | None = None


def _resumo(e: Espaco, papel: str) -> EspacoResumo:
    return EspacoResumo(id=e.id, sigla=e.sigla, nome=e.nome, tipo=e.tipo, modelo=e.modelo, meu_papel=papel)


def _detalhe(db: Session, usuario: Usuario, e: Espaco) -> EspacoDetalhe:
    papel = svc.papel_no_espaco(db, usuario, e) or ""
    return EspacoDetalhe(
        **_resumo(e, papel).model_dump(exclude={"paineis"}),
        descricao=e.descricao,
        criado_em=e.criado_em,
        permissoes=svc.permissoes_no_espaco(papel or None),
        paineis=[Opcao(id=p.id, nome=p.nome) for p in svc.listar_paineis(db, e)],
        tipos=[TipoSaida(id=t.id, nome=t.nome, nivel=t.nivel, padrao=t.espaco_id is None)
               for t in svc.listar_tipos(db, e)],
        status=[StatusSaida(id=s.id, nome=s.nome, categoria=s.categoria) for s in svc.listar_status(db, e)],
        origens=[Opcao(id=o.id, nome=o.nome) for o in svc.listar_origens(db, e)],
    )


# --- Espaços ----------------------------------------------------------------------------------

@rotas.get("/espacos", response_model=list[EspacoResumo])
def meus_espacos(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[EspacoResumo]:
    resumos = []
    for e, p in svc.listar_meus_espacos(db, usuario):
        resumo = _resumo(e, p)
        resumo.paineis = [Opcao(id=x.id, nome=x.nome) for x in svc.listar_paineis(db, e)]
        resumos.append(resumo)
    return resumos


@rotas.post("/espacos", response_model=EspacoDetalhe, status_code=201)
def criar_espaco(
    pedido: PedidoEspaco, request: Request, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> EspacoDetalhe:
    e = svc.criar_espaco(db, usuario, pedido.tipo, pedido.nome, pedido.sigla, pedido.modelo, ip_do_pedido(request))
    return _detalhe(db, usuario, e)


@rotas.get("/espacos/{sigla}", response_model=EspacoDetalhe)
def ver_espaco(sigla: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> EspacoDetalhe:
    return _detalhe(db, usuario, svc.buscar_espaco(db, usuario, sigla))


@rotas.patch("/espacos/{sigla}", response_model=EspacoDetalhe)
def editar_espaco(
    sigla: str, pedido: PedidoEditarEspaco, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> EspacoDetalhe:
    e = svc.buscar_espaco(db, usuario, sigla)
    svc.editar_espaco(db, usuario, e, pedido.nome, pedido.descricao)
    return _detalhe(db, usuario, e)


# --- Membros ----------------------------------------------------------------------------------

@rotas.get("/espacos/{sigla}/membros", response_model=list[MembroSaida])
def membros(sigla: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[MembroSaida]:
    e = svc.buscar_espaco(db, usuario, sigla)
    return [MembroSaida(usuario=PessoaResumo.de(m.usuario), papel=m.papel, adicionado_em=m.adicionado_em)
            for m in svc.listar_membros(db, e)]


@rotas.post("/espacos/{sigla}/membros", status_code=204)
def adicionar_membro(
    sigla: str, pedido: PedidoMembro, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    e = svc.buscar_espaco(db, usuario, sigla)
    svc.adicionar_membro(db, usuario, e, pedido.usuario_id, pedido.papel, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.patch("/espacos/{sigla}/membros/{usuario_id}", status_code=204)
def mudar_papel(
    sigla: str, usuario_id: uuid.UUID, pedido: PedidoPapelMembro, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    e = svc.buscar_espaco(db, usuario, sigla)
    svc.mudar_papel_membro(db, usuario, e, usuario_id, pedido.papel, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.delete("/espacos/{sigla}/membros/{usuario_id}", status_code=204)
def remover_membro(
    sigla: str, usuario_id: uuid.UUID, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    e = svc.buscar_espaco(db, usuario, sigla)
    svc.remover_membro(db, usuario, e, usuario_id, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.get("/pessoas", response_model=list[PessoaResumo])
def buscar_pessoas(
    busca: str = Query(min_length=2, max_length=100),
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> list[PessoaResumo]:
    """Busca de pessoas ativas para adicionar como membro (nome ou e-mail)."""
    termo = f"%{busca.strip().lower()}%"
    pessoas = db.scalars(
        select(Usuario).where(Usuario.ativo, or_(Usuario.email.like(termo), Usuario.nome.ilike(termo)))
        .order_by(Usuario.nome).limit(10)
    )
    return [PessoaResumo.de(p) for p in pessoas]


# --- Painéis, tipos e origens -----------------------------------------------------------------

def _uso(db: Session, coluna, valor) -> int:
    """Quantos itens usam um painel ou tipo. Os itens chegam na parte 2 da Etapa 2."""
    from ..modelos_itens import Item  # importação tardia para evitar ciclo

    return db.scalar(select(func.count()).select_from(Item).where(getattr(Item, coluna) == valor,
                                                                 Item.excluido_em.is_(None))) or 0


@rotas.post("/espacos/{sigla}/paineis", response_model=Opcao, status_code=201)
def criar_painel(
    sigla: str, pedido: PedidoNome, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Opcao:
    e = svc.buscar_espaco(db, usuario, sigla)
    p = svc.criar_painel(db, usuario, e, pedido.nome)
    return Opcao(id=p.id, nome=p.nome)


@rotas.patch("/espacos/{sigla}/paineis/{painel_id}", status_code=204)
def renomear_painel(
    sigla: str, painel_id: uuid.UUID, pedido: PedidoNome,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    e = svc.buscar_espaco(db, usuario, sigla)
    svc.renomear_painel(db, usuario, e, painel_id, pedido.nome)
    return Response(status_code=204)


@rotas.delete("/espacos/{sigla}/paineis/{painel_id}", status_code=204)
def excluir_painel(
    sigla: str, painel_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    e = svc.buscar_espaco(db, usuario, sigla)
    svc.excluir_painel(db, usuario, e, painel_id, _uso(db, "painel_id", painel_id))
    return Response(status_code=204)


@rotas.post("/espacos/{sigla}/tipos", response_model=TipoSaida, status_code=201)
def criar_tipo(
    sigla: str, pedido: PedidoNome, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> TipoSaida:
    e = svc.buscar_espaco(db, usuario, sigla)
    t = svc.criar_tipo(db, usuario, e, pedido.nome)
    return TipoSaida(id=t.id, nome=t.nome, nivel=t.nivel, padrao=False)


@rotas.patch("/espacos/{sigla}/tipos/{tipo_id}", status_code=204)
def renomear_tipo(
    sigla: str, tipo_id: uuid.UUID, pedido: PedidoNome,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    e = svc.buscar_espaco(db, usuario, sigla)
    svc.renomear_tipo(db, usuario, e, tipo_id, pedido.nome)
    return Response(status_code=204)


@rotas.delete("/espacos/{sigla}/tipos/{tipo_id}", status_code=204)
def excluir_tipo(
    sigla: str, tipo_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    e = svc.buscar_espaco(db, usuario, sigla)
    svc.excluir_tipo(db, usuario, e, tipo_id, _uso(db, "tipo_id", tipo_id))
    return Response(status_code=204)


@rotas.post("/espacos/{sigla}/origens", response_model=Opcao, status_code=201)
def criar_origem(
    sigla: str, pedido: PedidoNome, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Opcao:
    e = svc.buscar_espaco(db, usuario, sigla)
    o = svc.criar_origem(db, usuario, e, pedido.nome)
    return Opcao(id=o.id, nome=o.nome)


@rotas.delete("/espacos/{sigla}/origens/{origem_id}", status_code=204)
def desativar_origem(
    sigla: str, origem_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    e = svc.buscar_espaco(db, usuario, sigla)
    svc.desativar_origem(db, usuario, e, origem_id)
    return Response(status_code=204)


# --- Times provisórios ------------------------------------------------------------------------

@rotas.get("/times", response_model=list[TimeSaida])
def listar_times(
    todos: bool = False, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> list[TimeSaida]:
    return [TimeSaida(id=t.id, nome=t.nome, ativo=t.ativo) for t in times.listar(db, incluir_inativos=todos)]


@rotas.post("/admin/times", response_model=TimeSaida, status_code=201)
def criar_time(
    pedido: PedidoNome, request: Request, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> TimeSaida:
    t = times.criar(db, usuario, pedido.nome, ip_do_pedido(request))
    return TimeSaida(id=t.id, nome=t.nome, ativo=t.ativo)


@rotas.patch("/admin/times/{time_id}", status_code=204)
def alterar_time(
    time_id: uuid.UUID, pedido: PedidoTime, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    times.alterar(db, usuario, time_id, pedido.nome, pedido.ativo)
    return Response(status_code=204)
