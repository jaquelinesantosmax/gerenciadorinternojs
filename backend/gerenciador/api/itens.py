"""Rotas de itens, campos personalizados, comentários, anexos e vínculos."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import anexos as anexos_svc
from .. import campos as campos_svc
from .. import comentarios as comentarios_svc
from .. import espacos as espacos_svc
from .. import itens as itens_svc
from .. import times as times_svc
from .. import vinculos as vinculos_svc
from ..armazenamento import obter_armazenamento
from ..banco import obter_db
from ..modelos import Usuario
from ..modelos_espacos import Espaco, OpcaoOrigem, Painel, StatusItem, TimeProvisorio, TipoItem
from ..modelos_itens import PRIORIDADES, TIPOS_CAMPO, TIPOS_VINCULO, HistoricoItem, Item
from .deps import ip_do_pedido, usuario_atual
from .esquemas import PessoaResumo

rotas = APIRouter(prefix="/api")


# --- Formatos ---------------------------------------------------------------------------------

class Ref(BaseModel):
    id: uuid.UUID
    nome: str


class StatusRef(Ref):
    categoria: str


class ItemLinha(BaseModel):
    id: uuid.UUID
    chave: str
    resumo: str
    tipo: Ref
    nivel: str
    status: StatusRef
    prioridade: str
    responsavel: PessoaResumo | None
    data_entrega: date
    painel: Ref | None
    # Vínculos aparecem como coluna e filtro na Lista (docs/decisoes-de-desenho.md).
    bloqueado_por: list[str] = []


class ItemCurto(BaseModel):
    chave: str
    resumo: str
    tipo: str
    status: str
    status_categoria: str


class AnexoSaida(BaseModel):
    id: uuid.UUID
    nome_arquivo: str
    tipo_mime: str
    tamanho: int
    enviado_por: PessoaResumo | None
    enviado_em: datetime
    link: str
    pre_visualizacao: bool
    pode_excluir: bool


class VinculoSaida(BaseModel):
    id: uuid.UUID
    tipo: str
    rotulo: str
    chave: str
    acesso_restrito: bool
    resumo: str | None
    status: str | None
    status_categoria: str | None
    bloqueio_aberto: bool
    pedido_pendente: bool = False


class ItemDetalhe(BaseModel):
    id: uuid.UUID
    chave: str
    espaco: Ref
    espaco_sigla: str
    tipo: Ref
    nivel: str
    resumo: str
    descricao: dict[str, Any] | None
    status: StatusRef
    prioridade: str
    responsavel: PessoaResumo | None
    relator: PessoaResumo | None
    co_responsaveis: list[PessoaResumo]
    time: Ref
    data_inicio: date
    data_entrega: date
    data_real_entrega: date | None
    justificativa_atraso: str | None
    estimativa: Decimal | None
    estimativa_horas: Decimal | None
    pai: ItemCurto | None
    filhos: list[ItemCurto]
    painel: Ref | None
    origem: Ref | None
    categorias: list[str]
    valores: dict[str, Any]
    criado_em: datetime
    atualizado_em: datetime
    anexos: list[AnexoSaida]
    vinculos: list[VinculoSaida]
    permissoes: dict[str, bool]
    pode_excluir: bool


class CampoSaida(BaseModel):
    id: uuid.UUID
    nome: str
    tipo: str
    obrigatorio: bool
    tipos_item: list[uuid.UUID]
    config: dict[str, Any]
    ativo: bool


class OpcoesFormulario(BaseModel):
    responsaveis: list[PessoaResumo]
    membros: list[PessoaResumo]
    times: list[Ref]
    campos: list[CampoSaida]
    categorias: list[str]
    prioridades: dict[str, str]
    tipos_campo: dict[str, str]
    tipos_vinculo: dict[str, list[str]]
    moedas: dict[str, str]


class PedidoItem(BaseModel):
    dados: dict[str, Any]
    confirmar_bloqueio: bool = False


class PedidoCampo(BaseModel):
    nome: str = Field(max_length=200)
    tipo: str
    obrigatorio: bool = False
    tipos_item: list[uuid.UUID]
    config: dict[str, Any] = {}


class PedidoEditarCampo(BaseModel):
    nome: str | None = Field(default=None, max_length=200)
    obrigatorio: bool | None = None
    tipos_item: list[uuid.UUID] | None = None
    config: dict[str, Any] | None = None
    ativo: bool | None = None


class PedidoComentario(BaseModel):
    corpo: dict[str, Any]


class EventoAtividade(BaseModel):
    tipo: str  # comentario | historico
    id: str
    quando: datetime
    autor: PessoaResumo | None
    # Comentário
    corpo: dict[str, Any] | None = None
    editado_em: datetime | None = None
    excluido_em: datetime | None = None
    excluido_por: PessoaResumo | None = None
    pode_editar: bool = False
    # Histórico
    campo: str | None = None
    valor_anterior: str | None = None
    valor_novo: str | None = None


class PedidoVinculo(BaseModel):
    tipo: str
    sentido: str = "saida"
    chave: str = Field(max_length=24)
    confirmar_ciclo: bool = False


class LimiteAnexos(BaseModel):
    limite_mb: int


# --- Montagem das respostas -------------------------------------------------------------------

def _pessoa(db: Session, uid: uuid.UUID | None) -> PessoaResumo | None:
    return PessoaResumo.de(db.get(Usuario, uid)) if uid else None


def _ref(obj) -> Ref | None:
    return Ref(id=obj.id, nome=obj.nome) if obj else None


def _curto(db: Session, espaco: Espaco, item: Item) -> ItemCurto:
    status = db.get(StatusItem, item.status_id)
    return ItemCurto(chave=itens_svc.chave(espaco, item), resumo=item.resumo, tipo=db.get(TipoItem, item.tipo_id).nome,
                     status=status.nome, status_categoria=status.categoria)


def _linha(db: Session, espaco: Espaco, item: Item) -> ItemLinha:
    tipo = db.get(TipoItem, item.tipo_id)
    status = db.get(StatusItem, item.status_id)
    return ItemLinha(
        id=item.id, chave=itens_svc.chave(espaco, item), resumo=item.resumo, tipo=_ref(tipo), nivel=tipo.nivel,
        status=StatusRef(id=status.id, nome=status.nome, categoria=status.categoria), prioridade=item.prioridade,
        responsavel=_pessoa(db, item.responsavel_id), data_entrega=item.data_entrega,
        painel=_ref(db.get(Painel, item.painel_id)) if item.painel_id else None,
        bloqueado_por=vinculos_svc.chaves_que_bloqueiam(db, item) if status.categoria != "concluido" else [],
    )


def _anexos(db: Session, usuario: Usuario, espaco: Espaco, item: Item) -> list[AnexoSaida]:
    pode_todos = espacos_svc.pode_no_espaco(db, usuario, espaco, "excluir_qualquer_anexo")
    pode_proprios = espacos_svc.pode_no_espaco(db, usuario, espaco, "anexar")
    return [
        AnexoSaida(
            id=a.id, nome_arquivo=a.nome_arquivo, tipo_mime=a.tipo_mime, tamanho=a.tamanho,
            enviado_por=_pessoa(db, a.enviado_por_id), enviado_em=a.enviado_em,
            link=anexos_svc.link_temporario(a),
            pre_visualizacao=anexos_svc.pode_abrir_no_navegador(a) is not None,
            pode_excluir=pode_todos or (pode_proprios and a.enviado_por_id == usuario.id),
        )
        for a in anexos_svc.listar(db, item)
    ]


def _detalhe(db: Session, usuario: Usuario, item: Item, espaco: Espaco) -> ItemDetalhe:
    tipo = db.get(TipoItem, item.tipo_id)
    status = db.get(StatusItem, item.status_id)
    pai = db.get(Item, item.pai_id) if item.pai_id else None
    permissoes = espacos_svc.permissoes_do_usuario(db, usuario, espaco)
    return ItemDetalhe(
        id=item.id, chave=itens_svc.chave(espaco, item), espaco=Ref(id=espaco.id, nome=espaco.nome),
        espaco_sigla=espaco.sigla, tipo=_ref(tipo), nivel=tipo.nivel, resumo=item.resumo, descricao=item.descricao,
        status=StatusRef(id=status.id, nome=status.nome, categoria=status.categoria), prioridade=item.prioridade,
        responsavel=_pessoa(db, item.responsavel_id), relator=_pessoa(db, item.relator_id),
        co_responsaveis=[p for p in (_pessoa(db, u) for u in itens_svc.co_responsaveis(db, item)) if p],
        time=_ref(db.get(TimeProvisorio, item.time_id)), data_inicio=item.data_inicio,
        data_entrega=item.data_entrega, data_real_entrega=item.data_real_entrega,
        justificativa_atraso=item.justificativa_atraso, estimativa=item.estimativa,
        estimativa_horas=item.estimativa_horas,
        pai=_curto(db, espaco, pai) if pai and pai.excluido_em is None else None,
        filhos=[_curto(db, espaco, f) for f in itens_svc.filhos(db, item)],
        painel=_ref(db.get(Painel, item.painel_id)) if item.painel_id else None,
        origem=_ref(db.get(OpcaoOrigem, item.origem_id)) if item.origem_id else None,
        categorias=item.categorias, valores=item.valores, criado_em=item.criado_em,
        atualizado_em=item.atualizado_em, anexos=_anexos(db, usuario, espaco, item),
        vinculos=[VinculoSaida(**v.__dict__) for v in vinculos_svc.listar(db, usuario, item)],
        permissoes=permissoes,
        pode_excluir=permissoes["excluir_qualquer_item"]
        or (permissoes["excluir_proprios_itens"] and item.relator_id == usuario.id),
    )


def _campo(c) -> CampoSaida:
    return CampoSaida(id=c.id, nome=c.nome, tipo=c.tipo, obrigatorio=c.obrigatorio, tipos_item=c.tipos_item,
                      config=c.config, ativo=c.ativo)


# --- Itens de um espaço -----------------------------------------------------------------------

@rotas.get("/espacos/{sigla}/itens", response_model=list[ItemLinha])
def listar_itens(
    sigla: str,
    busca: str | None = Query(default=None, max_length=200),
    tipo_id: uuid.UUID | None = None, status_id: uuid.UUID | None = None, painel_id: uuid.UUID | None = None,
    responsavel_id: uuid.UUID | None = None, nivel: str | None = None,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> list[ItemLinha]:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    itens = itens_svc.listar(db, espaco, itens_svc.Filtros(busca, tipo_id, status_id, painel_id, responsavel_id))
    linhas = [_linha(db, espaco, i) for i in itens]
    return [linha for linha in linhas if not nivel or linha.nivel == nivel]


@rotas.get("/espacos/{sigla}/opcoes-item", response_model=OpcoesFormulario)
def opcoes_item(sigla: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> OpcoesFormulario:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    if espaco.tipo == "pessoal":
        membros = [PessoaResumo.de(db.get(Usuario, espaco.dono_id))]
        responsaveis = membros
    else:
        todos = espacos_svc.listar_membros(db, espaco)
        membros = [PessoaResumo.de(m.usuario) for m in todos if m.usuario.ativo]
        responsaveis = [PessoaResumo.de(m.usuario) for m in todos if m.usuario.ativo and m.papel in ("adm", "membro")]
    from ..campos import MOEDAS

    return OpcoesFormulario(
        responsaveis=responsaveis, membros=membros,
        times=[Ref(id=t.id, nome=t.nome) for t in times_svc.listar(db)],
        campos=[_campo(c) for c in campos_svc.listar(db, espaco)],
        categorias=itens_svc.categorias_do_espaco(db, espaco),
        prioridades=PRIORIDADES, tipos_campo=TIPOS_CAMPO,
        tipos_vinculo={k: list(v) for k, v in TIPOS_VINCULO.items()}, moedas=MOEDAS,
    )


@rotas.post("/espacos/{sigla}/itens", response_model=ItemDetalhe, status_code=201)
def criar_item(
    sigla: str, pedido: PedidoItem, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> ItemDetalhe:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    item = itens_svc.criar(db, usuario, espaco, pedido.dados)
    return _detalhe(db, usuario, item, espaco)


# --- Campos personalizados --------------------------------------------------------------------

@rotas.get("/espacos/{sigla}/campos", response_model=list[CampoSaida])
def listar_campos(
    sigla: str, todos: bool = False, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> list[CampoSaida]:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    return [_campo(c) for c in campos_svc.listar(db, espaco, incluir_inativos=todos)]


@rotas.post("/espacos/{sigla}/campos", response_model=CampoSaida, status_code=201)
def criar_campo(
    sigla: str, pedido: PedidoCampo, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> CampoSaida:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    return _campo(campos_svc.criar(db, usuario, espaco, pedido.nome, pedido.tipo, pedido.obrigatorio,
                                   pedido.tipos_item, pedido.config))


@rotas.patch("/espacos/{sigla}/campos/{campo_id}", response_model=CampoSaida)
def editar_campo(
    sigla: str, campo_id: uuid.UUID, pedido: PedidoEditarCampo,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> CampoSaida:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    return _campo(campos_svc.editar(db, usuario, espaco, campo_id, **pedido.model_dump(exclude_unset=True)))


# --- Um item ----------------------------------------------------------------------------------

@rotas.get("/itens/busca", response_model=list[ItemCurto])
def buscar_itens(
    q: str = Query(min_length=1, max_length=100), usuario: Usuario = Depends(usuario_atual),
    db: Session = Depends(obter_db),
) -> list[ItemCurto]:
    """Busca para vincular itens: pela chave (qualquer espaço que a pessoa vê) ou pelo resumo nos espaços dela."""
    achado = itens_svc.localizar(db, q)
    if achado and espacos_svc.pode_no_espaco(db, usuario, achado[1], "ver"):
        return [_curto(db, achado[1], achado[0])]
    meus = [e for e, _ in espacos_svc.listar_meus_espacos(db, usuario)]
    if not meus:
        return []
    linhas = db.execute(
        select(Item, Espaco).join(Espaco, Espaco.id == Item.espaco_id)
        .where(Item.espaco_id.in_([e.id for e in meus]), Item.excluido_em.is_(None), Item.resumo.ilike(f"%{q}%"))
        .order_by(Item.atualizado_em.desc()).limit(10)
    ).all()
    return [_curto(db, e, i) for i, e in linhas]


@rotas.get("/itens/{chave}", response_model=ItemDetalhe)
def ver_item(chave: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> ItemDetalhe:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    return _detalhe(db, usuario, item, espaco)


@rotas.patch("/itens/{chave}", response_model=ItemDetalhe)
def editar_item(
    chave: str, pedido: PedidoItem, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> ItemDetalhe:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    try:
        itens_svc.editar(db, usuario, item, espaco, pedido.dados, confirmar_bloqueio=pedido.confirmar_bloqueio,
                         ip=ip_do_pedido(request))
    except itens_svc.AvisoConcluirBloqueado as aviso:
        db.rollback()
        raise HTTPException(status_code=409, detail={"mensagem": aviso.mensagem, "codigo": "concluir_bloqueado",
                                                     "bloqueios": aviso.bloqueios}) from aviso
    return _detalhe(db, usuario, item, espaco)


@rotas.delete("/itens/{chave}", status_code=204)
def excluir_item(
    chave: str, request: Request, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    itens_svc.excluir(db, usuario, item, espaco, ip_do_pedido(request))
    return Response(status_code=204)


class PedidoClonar(BaseModel):
    copiar_comentarios: bool = False
    copiar_anexos: bool = False


@rotas.post("/itens/{chave}/clonar", response_model=ItemDetalhe, status_code=201)
def clonar_item(
    chave: str, pedido: PedidoClonar | None = None,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> ItemDetalhe:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    pedido = pedido or PedidoClonar()
    copia = itens_svc.clonar(db, usuario, item, espaco, copiar_comentarios=pedido.copiar_comentarios,
                             copiar_anexos=pedido.copiar_anexos)
    return _detalhe(db, usuario, copia, espaco)


# --- Atividade: comentários e histórico -------------------------------------------------------

@rotas.get("/itens/{chave}/atividade", response_model=list[EventoAtividade])
def atividade(
    chave: str, filtro: str = Query(default="tudo", pattern="^(tudo|comentarios|historico)$"),
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> list[EventoAtividade]:
    """Comentários, Histórico e Atividade (os dois juntos), sempre do mais recente para o mais antigo."""
    item, espaco = itens_svc.buscar(db, usuario, chave)
    eventos: list[EventoAtividade] = []
    if filtro in ("tudo", "comentarios"):
        pode_todos = espacos_svc.pode_no_espaco(db, usuario, espaco, "editar_qualquer_comentario")
        pode_comentar = espacos_svc.pode_no_espaco(db, usuario, espaco, "comentar")
        for c in comentarios_svc.listar(db, item):
            excluido = c.excluido_em is not None
            eventos.append(EventoAtividade(
                tipo="comentario", id=str(c.id), quando=c.criado_em, autor=_pessoa(db, c.autor_id),
                corpo=None if excluido else c.corpo, editado_em=c.editado_em, excluido_em=c.excluido_em,
                excluido_por=_pessoa(db, c.excluido_por_id),
                pode_editar=not excluido and (pode_todos or (pode_comentar and c.autor_id == usuario.id)),
            ))
    if filtro in ("tudo", "historico"):
        for h in db.scalars(select(HistoricoItem).where(HistoricoItem.item_id == item.id)):
            eventos.append(EventoAtividade(
                tipo="historico", id=str(h.id), quando=h.ocorrido_em, autor=_pessoa(db, h.autor_id),
                campo=h.campo, valor_anterior=h.valor_anterior, valor_novo=h.valor_novo,
            ))
    return sorted(eventos, key=lambda e: (e.quando, e.tipo == "comentario"), reverse=True)


@rotas.post("/itens/{chave}/comentarios", status_code=201, response_model=EventoAtividade)
def comentar(
    chave: str, pedido: PedidoComentario, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> EventoAtividade:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    c = comentarios_svc.criar(db, usuario, item, espaco, pedido.corpo)
    return EventoAtividade(tipo="comentario", id=str(c.id), quando=c.criado_em, autor=_pessoa(db, c.autor_id),
                           corpo=c.corpo, pode_editar=True)


@rotas.patch("/itens/{chave}/comentarios/{comentario_id}", status_code=204)
def editar_comentario(
    chave: str, comentario_id: uuid.UUID, pedido: PedidoComentario,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    comentarios_svc.editar(db, usuario, item, espaco, comentario_id, pedido.corpo)
    return Response(status_code=204)


@rotas.delete("/itens/{chave}/comentarios/{comentario_id}", status_code=204)
def excluir_comentario(
    chave: str, comentario_id: uuid.UUID, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    comentarios_svc.excluir(db, usuario, item, espaco, comentario_id, ip_do_pedido(request))
    return Response(status_code=204)


# --- Anexos -----------------------------------------------------------------------------------

@rotas.post("/itens/{chave}/anexos", response_model=list[AnexoSaida], status_code=201)
def enviar_anexos(
    chave: str, arquivos: list[UploadFile] = File(...),
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> list[AnexoSaida]:
    """Vários arquivos de uma vez (arrastar e soltar, colar print)."""
    item, espaco = itens_svc.buscar(db, usuario, chave)
    novos = {anexos_svc.enviar(db, usuario, item, espaco, a.filename or "arquivo", a.file).id for a in arquivos}
    return [a for a in _anexos(db, usuario, espaco, item) if a.id in novos]


@rotas.delete("/itens/{chave}/anexos/{anexo_id}", status_code=204)
def excluir_anexo(
    chave: str, anexo_id: uuid.UUID, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    anexo = anexos_svc.buscar(db, anexo_id)
    if anexo.item_id != item.id:
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
    anexos_svc.excluir(db, usuario, item, espaco, anexo, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.get("/anexos/{anexo_id}/conteudo")
def conteudo_anexo(
    anexo_id: uuid.UUID, expira: int, assinatura: str = Query(max_length=128), baixar: bool = False,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> StreamingResponse:
    """Precisa do link temporário válido E de acesso ao item."""
    if not anexos_svc.link_valido(anexo_id, expira, assinatura):
        raise HTTPException(status_code=403, detail="Este link expirou. Abra o item de novo para baixar.")
    anexo = anexos_svc.buscar(db, anexo_id)
    item = db.get(Item, anexo.item_id)
    espaco = db.get(Espaco, item.espaco_id)
    if item.excluido_em is not None or not espacos_svc.pode_no_espaco(db, usuario, espaco, "ver"):
        raise HTTPException(status_code=404, detail="Anexo não encontrado.")
    tipo_navegador = None if baixar else anexos_svc.pode_abrir_no_navegador(anexo)
    nome = anexo.nome_arquivo.replace('"', "")
    from urllib.parse import quote

    disposicao = "inline" if tipo_navegador else "attachment"
    cabecalhos = {
        "Content-Disposition": f"{disposicao}; filename*=UTF-8''{quote(nome)}",
        "X-Content-Type-Options": "nosniff",
        # Mesmo que algo escape, o navegador não executa nada vindo daqui.
        "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'; sandbox",
        "Cache-Control": "private, max-age=300",
        "Content-Length": str(anexo.tamanho),
    }
    return StreamingResponse(obter_armazenamento().ler(anexo.chave_armazenamento),
                             media_type=tipo_navegador or "application/octet-stream", headers=cabecalhos)


@rotas.get("/admin/limite-anexos", response_model=LimiteAnexos)
def ver_limite(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> LimiteAnexos:
    return LimiteAnexos(limite_mb=anexos_svc.limite_mb(db))


@rotas.put("/admin/limite-anexos", status_code=204)
def definir_limite(
    pedido: LimiteAnexos, request: Request, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    anexos_svc.definir_limite(db, usuario, pedido.limite_mb, ip_do_pedido(request))
    return Response(status_code=204)


# --- Vínculos ---------------------------------------------------------------------------------

@rotas.post("/itens/{chave}/vinculos", status_code=201, response_model=list[VinculoSaida])
def vincular(
    chave: str, pedido: PedidoVinculo, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> list[VinculoSaida]:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    achado = itens_svc.localizar(db, pedido.chave)
    if achado is None or not espacos_svc.pode_no_espaco(db, usuario, achado[1], "ver"):
        raise HTTPException(status_code=404, detail=f"Item {pedido.chave.upper()} não encontrado.")
    try:
        vinculos_svc.criar(db, usuario, item, espaco, pedido.tipo, pedido.sentido, achado[0], achado[1],
                           confirmar_ciclo=pedido.confirmar_ciclo)
    except vinculos_svc.AvisoBloqueioCircular as aviso:
        raise HTTPException(status_code=409, detail={"mensagem": aviso.mensagem, "codigo": "bloqueio_circular"}) from aviso
    return [VinculoSaida(**v.__dict__) for v in vinculos_svc.listar(db, usuario, item)]


@rotas.delete("/itens/{chave}/vinculos/{vinculo_id}", status_code=204)
def desvincular(
    chave: str, vinculo_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    item, espaco = itens_svc.buscar(db, usuario, chave)
    vinculos_svc.remover(db, usuario, item, espaco, vinculo_id)
    return Response(status_code=204)
