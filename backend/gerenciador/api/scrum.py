"""Rotas da Etapa 3b: sprints, backlog do Scrum e métricas."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .. import espacos as espacos_svc
from .. import itens as itens_svc
from .. import scrum
from ..banco import obter_db
from ..modelos import Usuario
from ..modelos_espacos import Espaco
from ..modelos_quadros import Quadro
from ..modelos_scrum import UNIDADES_ESTIMATIVA, Sprint
from .deps import usuario_atual
from .quadros import Card, cards_de

rotas = APIRouter(prefix="/api")


class SprintSaida(BaseModel):
    id: uuid.UUID
    nome: str
    objetivo: str | None
    inicio: date | None
    fim: date | None
    estado: str
    compromisso: Decimal | None
    entregue: Decimal | None
    total: Decimal
    itens: list[Card]


class Planejamento(BaseModel):
    unidade: str
    nome_unidade: str
    sprints: list[SprintSaida]
    backlog: list[Card]
    backlog_total: Decimal
    pode_gerenciar: bool


class PedidoSprint(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    objetivo: str | None = Field(default=None, max_length=2000)
    inicio: date | None = None
    fim: date | None = None


class PedidoItemSprint(BaseModel):
    chave: str = Field(max_length=24)


class PedidoEncerrar(BaseModel):
    destino: str = "backlog"


class PedidoUnidade(BaseModel):
    unidade: str


class PontoBurndown(BaseModel):
    dia: date
    restante: Decimal | None
    ideal: Decimal
    escopo: Decimal | None


class LinhaVelocidade(BaseModel):
    sprint: str
    compromisso: Decimal
    entregue: Decimal


class ItemRelatorio(BaseModel):
    chave: str
    resumo: str
    valor: Decimal


class RelatorioSaida(BaseModel):
    sprint: SprintSaida
    unidade: str
    concluidos: list[ItemRelatorio]
    nao_concluidos: list[ItemRelatorio]
    adicionados_depois: list[ItemRelatorio]
    removidos: list[ItemRelatorio]


class DiaFluxo(BaseModel):
    dia: date
    a_fazer: int
    em_andamento: int
    concluido: int


class CicloSaida(BaseModel):
    chave: str
    resumo: str
    inicio: datetime
    fim: datetime
    dias: float


class TempoDeCicloSaida(BaseModel):
    itens: list[CicloSaida]
    media: float | None
    mediana: float | None
    p85: float | None


# --- Auxiliares -------------------------------------------------------------------------------

def _quadro(db: Session, usuario: Usuario, quadro_id: uuid.UUID) -> tuple[Quadro, Espaco]:
    quadro = db.get(Quadro, quadro_id)
    if quadro is None:
        raise HTTPException(status_code=404, detail="Quadro não encontrado.")
    espaco = db.get(Espaco, quadro.espaco_id)
    if not espacos_svc.pode_no_espaco(db, usuario, espaco, "ver"):
        raise HTTPException(status_code=404, detail="Quadro não encontrado.")
    return quadro, espaco


def _sprint(db: Session, usuario: Usuario, sprint_id: uuid.UUID) -> tuple[Sprint, Quadro, Espaco]:
    sprint, quadro, espaco = scrum.buscar_sprint(db, sprint_id)
    if not espacos_svc.pode_no_espaco(db, usuario, espaco, "ver"):
        raise HTTPException(status_code=404, detail="Sprint não encontrada.")
    return sprint, quadro, espaco


def _sprint_saida(db: Session, sprint: Sprint, quadro: Quadro, espaco: Espaco) -> SprintSaida:
    itens = scrum.itens_da_sprint(db, sprint) if sprint.estado != "encerrada" else []
    return SprintSaida(
        id=sprint.id, nome=sprint.nome, objetivo=sprint.objetivo, inicio=sprint.inicio, fim=sprint.fim,
        estado=sprint.estado, compromisso=sprint.compromisso, entregue=sprint.entregue,
        total=scrum.total(db, itens, quadro.unidade_estimativa), itens=cards_de(db, espaco, itens),
    )


def _item_do_quadro(db: Session, usuario: Usuario, chave: str):
    item, _ = itens_svc.buscar(db, usuario, chave)
    return item


def _itens_relatorio(espaco: Espaco, itens, unidade: str) -> list[ItemRelatorio]:
    return [ItemRelatorio(chave=itens_svc.chave(espaco, i), resumo=i.resumo, valor=scrum.valor(i, unidade)) for i in itens]


# --- Planejamento -----------------------------------------------------------------------------

@rotas.get("/quadros/{quadro_id}/planejamento", response_model=Planejamento)
def planejamento(quadro_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> Planejamento:
    """Backlog e sprints abertas (ativas e planejadas) de um quadro Scrum."""
    quadro, espaco = _quadro(db, usuario, quadro_id)
    abertas = [s for s in scrum.sprints_do_quadro(db, quadro) if s.estado != "encerrada"]
    backlog = scrum.backlog(db, quadro)
    return Planejamento(
        unidade=quadro.unidade_estimativa, nome_unidade=UNIDADES_ESTIMATIVA[quadro.unidade_estimativa],
        sprints=[_sprint_saida(db, s, quadro, espaco) for s in abertas],
        backlog=cards_de(db, espaco, backlog), backlog_total=scrum.total(db, backlog, quadro.unidade_estimativa),
        pode_gerenciar=espacos_svc.pode_no_espaco(db, usuario, espaco, "gerenciar_sprints"),
    )


@rotas.get("/quadros/{quadro_id}/sprints", response_model=list[SprintSaida])
def todas_as_sprints(
    quadro_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> list[SprintSaida]:
    quadro, espaco = _quadro(db, usuario, quadro_id)
    return [_sprint_saida(db, s, quadro, espaco) for s in scrum.sprints_do_quadro(db, quadro)]


@rotas.put("/quadros/{quadro_id}/unidade", status_code=204)
def definir_unidade(
    quadro_id: uuid.UUID, pedido: PedidoUnidade, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    quadro, _ = _quadro(db, usuario, quadro_id)
    scrum.definir_unidade(db, usuario, quadro, pedido.unidade)
    return Response(status_code=204)


@rotas.post("/quadros/{quadro_id}/sprints", response_model=SprintSaida, status_code=201)
def criar_sprint(
    quadro_id: uuid.UUID, pedido: PedidoSprint, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> SprintSaida:
    quadro, espaco = _quadro(db, usuario, quadro_id)
    sprint = scrum.criar_sprint(db, usuario, quadro, pedido.nome, pedido.objetivo, pedido.inicio, pedido.fim)
    return _sprint_saida(db, sprint, quadro, espaco)


@rotas.patch("/sprints/{sprint_id}", response_model=SprintSaida)
def editar_sprint(
    sprint_id: uuid.UUID, pedido: PedidoSprint, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> SprintSaida:
    sprint, quadro, espaco = _sprint(db, usuario, sprint_id)
    scrum.editar_sprint(db, usuario, sprint, quadro, **pedido.model_dump(exclude_unset=True))
    return _sprint_saida(db, sprint, quadro, espaco)


@rotas.delete("/sprints/{sprint_id}", status_code=204)
def excluir_sprint(sprint_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> Response:
    sprint, quadro, _ = _sprint(db, usuario, sprint_id)
    scrum.excluir_sprint(db, usuario, sprint, quadro)
    return Response(status_code=204)


@rotas.post("/sprints/{sprint_id}/itens", status_code=204)
def adicionar_item(
    sprint_id: uuid.UUID, pedido: PedidoItemSprint, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    sprint, quadro, _ = _sprint(db, usuario, sprint_id)
    scrum.adicionar_item(db, usuario, sprint, quadro, _item_do_quadro(db, usuario, pedido.chave))
    return Response(status_code=204)


@rotas.delete("/sprints/{sprint_id}/itens/{chave}", status_code=204)
def remover_item(
    sprint_id: uuid.UUID, chave: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    sprint, quadro, _ = _sprint(db, usuario, sprint_id)
    scrum.remover_item(db, usuario, sprint, quadro, _item_do_quadro(db, usuario, chave))
    return Response(status_code=204)


@rotas.post("/sprints/{sprint_id}/iniciar", response_model=SprintSaida)
def iniciar(
    sprint_id: uuid.UUID, pedido: PedidoSprint, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> SprintSaida:
    sprint, quadro, espaco = _sprint(db, usuario, sprint_id)
    scrum.iniciar_sprint(db, usuario, sprint, quadro, pedido.inicio, pedido.fim)
    return _sprint_saida(db, sprint, quadro, espaco)


@rotas.post("/sprints/{sprint_id}/encerrar", response_model=RelatorioSaida)
def encerrar(
    sprint_id: uuid.UUID, pedido: PedidoEncerrar, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> RelatorioSaida:
    sprint, quadro, espaco = _sprint(db, usuario, sprint_id)
    scrum.encerrar_sprint(db, usuario, sprint, quadro, pedido.destino)
    return relatorio(sprint_id, usuario, db)


# --- Métricas ---------------------------------------------------------------------------------

@rotas.get("/sprints/{sprint_id}/burndown", response_model=list[PontoBurndown])
def burndown(sprint_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[PontoBurndown]:
    sprint, quadro, _ = _sprint(db, usuario, sprint_id)
    return [PontoBurndown(**p.__dict__) for p in scrum.burndown(db, sprint, quadro)]


@rotas.get("/sprints/{sprint_id}/relatorio", response_model=RelatorioSaida)
def relatorio(sprint_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> RelatorioSaida:
    sprint, quadro, espaco = _sprint(db, usuario, sprint_id)
    r = scrum.relatorio(db, sprint)
    u = quadro.unidade_estimativa
    return RelatorioSaida(
        sprint=_sprint_saida(db, sprint, quadro, espaco), unidade=u,
        concluidos=_itens_relatorio(espaco, r.concluidos, u), nao_concluidos=_itens_relatorio(espaco, r.nao_concluidos, u),
        adicionados_depois=_itens_relatorio(espaco, r.adicionados_depois, u), removidos=_itens_relatorio(espaco, r.removidos, u),
    )


@rotas.get("/quadros/{quadro_id}/velocidade", response_model=list[LinhaVelocidade])
def velocidade(
    quadro_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> list[LinhaVelocidade]:
    quadro, _ = _quadro(db, usuario, quadro_id)
    return [LinhaVelocidade(**linha.__dict__) for linha in scrum.velocidade(db, quadro)]


@rotas.get("/quadros/{quadro_id}/fluxo-acumulado", response_model=list[DiaFluxo])
def fluxo_acumulado(
    quadro_id: uuid.UUID, dias: int = Query(default=30, ge=7, le=180),
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> list[DiaFluxo]:
    quadro, _ = _quadro(db, usuario, quadro_id)
    return [DiaFluxo(**d.__dict__) for d in scrum.fluxo_acumulado(db, quadro, dias)]


@rotas.get("/quadros/{quadro_id}/tempo-de-ciclo", response_model=TempoDeCicloSaida)
def tempo_de_ciclo(
    quadro_id: uuid.UUID, dias: int = Query(default=90, ge=7, le=365),
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> TempoDeCicloSaida:
    quadro, espaco = _quadro(db, usuario, quadro_id)
    t = scrum.tempo_de_ciclo(db, quadro, dias)
    return TempoDeCicloSaida(
        itens=[CicloSaida(chave=itens_svc.chave(espaco, c.item), resumo=c.item.resumo, inicio=c.inicio, fim=c.fim, dias=c.dias)
               for c in t.itens],
        media=t.media, mediana=t.mediana, p85=t.p85,
    )
