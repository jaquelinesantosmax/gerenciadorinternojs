"""Rotas da Etapa 3a: workflow (status e transições), quadros e Gantt."""

import uuid
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .. import espacos as espacos_svc
from .. import workflow as wf
from ..banco import obter_db
from ..modelos import Usuario
from ..modelos_espacos import Espaco, Painel, StatusItem, TipoItem
from ..modelos_itens import Item, Vinculo
from ..modelos_quadros import Quadro
from .deps import usuario_atual
from .esquemas import PessoaResumo

rotas = APIRouter(prefix="/api")


class StatusWorkflow(BaseModel):
    id: uuid.UUID
    nome: str
    categoria: str
    proprio: bool
    itens: int


class Workflow(BaseModel):
    ligados: list[StatusWorkflow]
    disponiveis: list[StatusWorkflow]
    transicoes: list[tuple[uuid.UUID, uuid.UUID]]


class PedidoStatus(BaseModel):
    nome: str = Field(max_length=120)
    categoria: str = "em_andamento"
    confirmar: bool = False


class PedidoTransicoes(BaseModel):
    pares: list[tuple[uuid.UUID, uuid.UUID]]


class QuadroResumo(BaseModel):
    id: uuid.UUID
    nome: str
    tipo: str
    painel_id: uuid.UUID | None
    usa_backlog: bool
    unidade_estimativa: str = "pontos"


class Card(BaseModel):
    chave: str
    resumo: str
    tipo: str
    nivel: str
    prioridade: str
    responsavel: PessoaResumo | None
    status_id: uuid.UUID
    status: str
    status_categoria: str
    data_entrega: date
    atrasado: bool
    bloqueado: bool
    painel: str | None
    estimativa: Decimal | None = None
    estimativa_horas: Decimal | None = None


class ColunaSaida(BaseModel):
    id: uuid.UUID
    nome: str
    limite: int | None
    status: list[StatusWorkflow]
    cards: list[Card]
    acima_do_limite: bool


class QuadroSaida(QuadroResumo):
    colunas: list[ColunaSaida]
    backlog: list[Card]
    sem_coluna: list[Card]
    # Para onde cada status pode ir, para a tela saber o que oferecer ao arrastar.
    destinos: dict[str, list[uuid.UUID]]


class PedidoQuadro(BaseModel):
    nome: str = Field(max_length=120)
    tipo: str = "kanban"


class PedidoAlterarQuadro(BaseModel):
    nome: str | None = Field(default=None, max_length=120)
    usa_backlog: bool | None = None


class PedidoColunas(BaseModel):
    colunas: list[dict]


class BarraGantt(BaseModel):
    chave: str
    resumo: str
    tipo: str
    nivel: str
    pai: str | None
    inicio: date
    entrega: date
    entrega_real: date | None
    status: str
    status_categoria: str
    responsavel: str | None
    painel_id: uuid.UUID | None


class Gantt(BaseModel):
    barras: list[BarraGantt]
    # Setas de dependência: [quem bloqueia, quem é bloqueado].
    bloqueios: list[tuple[str, str]]


def _exigir_avisos(func):
    """Converte o aviso de nome parecido em 409 com código, para a tela pedir confirmação."""
    try:
        return func()
    except wf.AvisoNomeParecido as aviso:
        raise HTTPException(status_code=409, detail={"mensagem": aviso.mensagem, "codigo": "status_parecido"}) from aviso


def _workflow(db: Session, espaco: Espaco) -> Workflow:
    ligados = wf.status_do_espaco(db, espaco)
    ids = {s.id for s in ligados}
    return Workflow(
        ligados=[StatusWorkflow(id=s.id, nome=s.nome, categoria=s.categoria, proprio=s.espaco_id == espaco.id,
                                itens=wf.itens_no_status(db, espaco, s.id)) for s in ligados],
        disponiveis=[StatusWorkflow(id=s.id, nome=s.nome, categoria=s.categoria, proprio=False, itens=0)
                     for s in wf.status_padrao(db) if s.id not in ids],
        transicoes=sorted(wf.transicoes(db, espaco), key=lambda p: (str(p[0]), str(p[1]))),
    )


# --- Workflow do espaço -----------------------------------------------------------------------

@rotas.get("/espacos/{sigla}/workflow", response_model=Workflow)
def ver_workflow(sigla: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> Workflow:
    return _workflow(db, espacos_svc.buscar_espaco(db, usuario, sigla))


@rotas.post("/espacos/{sigla}/status", response_model=Workflow, status_code=201)
def criar_status(
    sigla: str, pedido: PedidoStatus, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Workflow:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    _exigir_avisos(lambda: wf.criar_status(db, usuario, espaco, pedido.nome, pedido.categoria, pedido.confirmar))
    return _workflow(db, espaco)


@rotas.post("/espacos/{sigla}/status/{status_id}/ligar", response_model=Workflow)
def ligar_status(
    sigla: str, status_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Workflow:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    wf.ligar_status(db, usuario, espaco, status_id)
    return _workflow(db, espaco)


@rotas.patch("/espacos/{sigla}/status/{status_id}", response_model=Workflow)
def renomear_status(
    sigla: str, status_id: uuid.UUID, pedido: PedidoStatus,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Workflow:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    _exigir_avisos(lambda: wf.renomear_status(db, usuario, espaco, status_id, pedido.nome, pedido.confirmar))
    return _workflow(db, espaco)


@rotas.delete("/espacos/{sigla}/status/{status_id}", response_model=Workflow)
def desligar_status(
    sigla: str, status_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Workflow:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    wf.desligar_status(db, usuario, espaco, status_id)
    return _workflow(db, espaco)


@rotas.put("/espacos/{sigla}/transicoes", response_model=Workflow)
def definir_transicoes(
    sigla: str, pedido: PedidoTransicoes, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Workflow:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    wf.definir_transicoes(db, usuario, espaco, pedido.pares)
    return _workflow(db, espaco)


# --- Catálogo padrão (ADM da plataforma) ------------------------------------------------------

class StatusCatalogo(BaseModel):
    id: uuid.UUID
    nome: str
    categoria: str
    espaco: str | None


@rotas.get("/admin/status", response_model=list[StatusCatalogo])
def catalogo(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[StatusCatalogo]:
    from ..papeis import exigir

    exigir(db, usuario, "gerenciar_status_padrao")
    padrao = [StatusCatalogo(id=s.id, nome=s.nome, categoria=s.categoria, espaco=None) for s in wf.status_padrao(db)]
    proprios = [StatusCatalogo(id=s.id, nome=s.nome, categoria=s.categoria, espaco=e.sigla)
                for s, e in wf.status_proprios_de_todos(db)]
    return padrao + proprios


@rotas.post("/admin/status", response_model=list[StatusCatalogo], status_code=201)
def criar_status_padrao(
    pedido: PedidoStatus, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> list[StatusCatalogo]:
    _exigir_avisos(lambda: wf.criar_status_padrao(db, usuario, pedido.nome, pedido.categoria, pedido.confirmar))
    return catalogo(usuario, db)


@rotas.post("/admin/status/{status_id}/promover", response_model=list[StatusCatalogo])
def promover(status_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[StatusCatalogo]:
    wf.promover_status(db, usuario, status_id)
    return catalogo(usuario, db)


# --- Quadros ----------------------------------------------------------------------------------

def _quadro_do_usuario(db: Session, usuario: Usuario, quadro_id: uuid.UUID) -> tuple[Quadro, Espaco]:
    quadro = wf.buscar_quadro(db, quadro_id)
    espaco = db.get(Espaco, quadro.espaco_id)
    if not espacos_svc.pode_no_espaco(db, usuario, espaco, "ver"):
        raise HTTPException(status_code=404, detail="Quadro não encontrado.")
    return quadro, espaco


def _resumo(q: Quadro) -> QuadroResumo:
    return QuadroResumo(id=q.id, nome=q.nome, tipo=q.tipo, painel_id=q.painel_id, usa_backlog=q.usa_backlog,
                        unidade_estimativa=q.unidade_estimativa)


@rotas.get("/espacos/{sigla}/quadros", response_model=list[QuadroResumo])
def listar_quadros(sigla: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[QuadroResumo]:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    return [_resumo(q) for q in wf.quadros_do_espaco(db, espaco)]


@rotas.post("/espacos/{sigla}/quadros", response_model=QuadroResumo, status_code=201)
def criar_quadro(
    sigla: str, pedido: PedidoQuadro, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> QuadroResumo:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    return _resumo(wf.novo_quadro(db, usuario, espaco, pedido.nome, pedido.tipo))


def cards_de(db: Session, espaco: Espaco, itens: list[Item]) -> list[Card]:
    """Cards ordenados por prioridade e entrega."""
    from ..itens import chave as chave_item
    from ..scrum import hoje_brasilia
    from ..vinculos import chaves_que_bloqueiam

    status = {s.id: s for s in db.scalars(select(StatusItem))}
    tipos = {t.id: t for t in db.scalars(select(TipoItem))}
    paineis = {p.id: p.nome for p in db.scalars(select(Painel).where(Painel.espaco_id == espaco.id))}
    hoje = hoje_brasilia()
    ordem_prioridade = {"critica": 0, "alta": 1, "media": 2, "baixa": 3}

    def card(i: Item) -> Card:
        s = status[i.status_id]
        return Card(
            chave=chave_item(espaco, i), resumo=i.resumo, tipo=tipos[i.tipo_id].nome, nivel=tipos[i.tipo_id].nivel,
            prioridade=i.prioridade, responsavel=PessoaResumo.de(db.get(Usuario, i.responsavel_id)),
            status_id=s.id, status=s.nome, status_categoria=s.categoria, data_entrega=i.data_entrega,
            atrasado=s.categoria != "concluido" and i.data_entrega < hoje,
            bloqueado=s.categoria != "concluido" and bool(chaves_que_bloqueiam(db, i)),
            painel=paineis.get(i.painel_id) if i.painel_id else None,
            estimativa=i.estimativa, estimativa_horas=i.estimativa_horas,
        )

    return sorted((card(i) for i in itens), key=lambda c: (ordem_prioridade.get(c.prioridade, 9), c.data_entrega))


@rotas.get("/quadros/{quadro_id}", response_model=QuadroSaida)
def ver_quadro(
    quadro_id: uuid.UUID, sprint_id: uuid.UUID | None = None,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> QuadroSaida:
    """Colunas com os cards. Com sprint_id, mostra só os itens daquela sprint (quadro da sprint ativa)."""
    from .. import scrum

    quadro, espaco = _quadro_do_usuario(db, usuario, quadro_id)
    status = {s.id: s for s in wf.status_do_espaco(db, espaco)}
    if sprint_id:
        sprint, quadro_da_sprint, _ = scrum.buscar_sprint(db, sprint_id)
        if quadro_da_sprint.id != quadro.id:
            raise HTTPException(status_code=404, detail="Sprint não encontrada.")
        itens = scrum.itens_da_sprint(db, sprint)
    else:
        itens = scrum.itens_do_quadro(db, quadro)
    cards = cards_de(db, espaco, itens)
    colunas_saida, mapeados = [], set()
    for c in wf.colunas_do_quadro(db, quadro):
        mapeados |= set(c.status_ids)
        da_coluna = [x for x in cards if x.status_id in c.status_ids]
        colunas_saida.append(ColunaSaida(
            id=c.id, nome=c.nome, limite=c.limite, cards=da_coluna,
            status=[StatusWorkflow(id=s, nome=status[s].nome, categoria=status[s].categoria, proprio=False, itens=0)
                    for s in c.status_ids if s in status],
            acima_do_limite=c.limite is not None and len(da_coluna) > c.limite,
        ))
    fora = [x for x in cards if x.status_id not in mapeados]
    backlog = [x for x in fora if quadro.usa_backlog and x.status_categoria == "a_fazer" and not sprint_id]
    return QuadroSaida(
        **_resumo(quadro).model_dump(), colunas=colunas_saida, backlog=backlog,
        sem_coluna=[x for x in fora if x not in backlog],
        destinos={str(s): wf.destinos(db, espaco, s) for s in status},
    )


@rotas.patch("/quadros/{quadro_id}", response_model=QuadroResumo)
def alterar_quadro(
    quadro_id: uuid.UUID, pedido: PedidoAlterarQuadro, usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(obter_db),
) -> QuadroResumo:
    quadro, espaco = _quadro_do_usuario(db, usuario, quadro_id)
    wf.alterar_quadro(db, usuario, espaco, quadro, pedido.nome, pedido.usa_backlog)
    return _resumo(quadro)


@rotas.put("/quadros/{quadro_id}/colunas", status_code=204)
def definir_colunas(
    quadro_id: uuid.UUID, pedido: PedidoColunas, usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(obter_db),
) -> Response:
    quadro, espaco = _quadro_do_usuario(db, usuario, quadro_id)
    wf.definir_colunas(db, usuario, espaco, quadro, pedido.colunas)
    return Response(status_code=204)


@rotas.delete("/quadros/{quadro_id}", status_code=204)
def excluir_quadro(quadro_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> Response:
    quadro, espaco = _quadro_do_usuario(db, usuario, quadro_id)
    wf.excluir_quadro(db, usuario, espaco, quadro)
    return Response(status_code=204)


# --- Gantt ------------------------------------------------------------------------------------

@rotas.get("/espacos/{sigla}/gantt", response_model=Gantt)
def gantt(
    sigla: str, painel_id: uuid.UUID | None = None,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Gantt:
    from ..itens import chave as chave_item

    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    consulta = select(Item).where(Item.espaco_id == espaco.id, Item.excluido_em.is_(None))
    if painel_id:
        consulta = consulta.where(Item.painel_id == painel_id)
    itens = list(db.scalars(consulta.order_by(Item.data_inicio, Item.numero)))
    por_id = {i.id: i for i in itens}
    tipos = {t.id: t for t in db.scalars(select(TipoItem))}
    status = {s.id: s for s in db.scalars(select(StatusItem))}
    barras = [
        BarraGantt(
            chave=chave_item(espaco, i), resumo=i.resumo, tipo=tipos[i.tipo_id].nome, nivel=tipos[i.tipo_id].nivel,
            pai=chave_item(espaco, por_id[i.pai_id]) if i.pai_id in por_id else None,
            inicio=i.data_inicio, entrega=i.data_entrega, entrega_real=i.data_real_entrega,
            status=status[i.status_id].nome, status_categoria=status[i.status_id].categoria,
            responsavel=(u.nome if (u := db.get(Usuario, i.responsavel_id)) else None), painel_id=i.painel_id,
        )
        for i in itens
    ]
    # Setas só entre itens que aparecem no Gantt (vínculos com outros espaços ficam no detalhe do item).
    ids = list(por_id)
    bloqueios = [
        (chave_item(espaco, por_id[v.origem_id]), chave_item(espaco, por_id[v.destino_id]))
        for v in db.scalars(select(Vinculo).where(Vinculo.tipo == "bloqueia",
                                                  or_(Vinculo.origem_id.in_(ids), Vinculo.destino_id.in_(ids))))
        if v.origem_id in por_id and v.destino_id in por_id
    ]
    return Gantt(barras=barras, bloqueios=bloqueios)
