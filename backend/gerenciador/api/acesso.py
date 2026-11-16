"""Rotas da Etapa 4: times, acesso por time, Gestor, suporte, Solicitar acesso, espaço aberto, compartilhamento
e a lista de espaços para explorar."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import acesso
from .. import espacos as espacos_svc
from .. import itens as itens_svc
from .. import times as times_svc
from ..banco import obter_db
from ..modelos import Usuario
from ..modelos_espacos import Espaco
from ..papeis import ADM, GESTOR, papeis_ativos
from .deps import ip_do_pedido, usuario_atual
from .esquemas import PessoaResumo

rotas = APIRouter(prefix="/api")


class TimeDetalhe(BaseModel):
    id: uuid.UUID
    nome: str
    ativo: bool
    criado_por: PessoaResumo | None
    membros: list[PessoaResumo]
    pode_editar: bool


class GestaoTimes(BaseModel):
    pode_criar: bool
    times: list[TimeDetalhe]


class PedidoNome(BaseModel):
    nome: str = Field(max_length=200)


class PedidoPessoa(BaseModel):
    usuario_id: uuid.UUID


class PedidoTimeAcesso(BaseModel):
    time_id: uuid.UUID
    papel: str


class PedidoPapel(BaseModel):
    papel: str


class AcessoTimeSaida(BaseModel):
    time_id: uuid.UUID
    nome: str
    papel: str
    membros: int


class PedidoSim(BaseModel):
    sim: bool


class PedidoMotivo(BaseModel):
    motivo: str = Field(max_length=2000)


class PedidoMensagem(BaseModel):
    mensagem: str | None = Field(default=None, max_length=1000)


class PedidoSaida(BaseModel):
    id: uuid.UUID
    pessoa: PessoaResumo
    item_chave: str | None
    mensagem: str | None
    criado_em: datetime


class GestorSaida(BaseModel):
    pessoa: PessoaResumo
    desde: datetime


class EspacoExplorar(BaseModel):
    sigla: str
    nome: str
    aberto: bool
    meu_papel: str | None
    acompanha: bool
    em_suporte: bool


class PedidoAberto(BaseModel):
    aberto: bool


def _espaco_bruto(db: Session, sigla: str) -> Espaco:
    """Busca sem conferir acesso (para suporte e Solicitar acesso). A regra de cada ação confere o resto."""
    espaco = db.scalar(select(Espaco).where(Espaco.sigla == sigla.upper()))
    if espaco is None:
        raise HTTPException(status_code=404, detail="Espaço não encontrado.")
    return espaco


def _time_detalhe(db: Session, usuario: Usuario, t) -> TimeDetalhe:
    return TimeDetalhe(
        id=t.id, nome=t.nome, ativo=t.ativo,
        criado_por=PessoaResumo.de(db.get(Usuario, t.criado_por_id)) if t.criado_por_id else None,
        membros=[PessoaResumo.de(u) for u in times_svc.membros(db, t)],
        pode_editar=times_svc.pode_editar(db, usuario, t),
    )


# --- Times ------------------------------------------------------------------------------------

@rotas.get("/times/gestao", response_model=GestaoTimes)
def gestao_times(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> GestaoTimes:
    return GestaoTimes(pode_criar=times_svc.pode_criar(db, usuario),
                       times=[_time_detalhe(db, usuario, t) for t in times_svc.listar(db, incluir_inativos=True)])


@rotas.post("/times", response_model=TimeDetalhe, status_code=201)
def criar_time(pedido: PedidoNome, request: Request, usuario: Usuario = Depends(usuario_atual),
               db: Session = Depends(obter_db)) -> TimeDetalhe:
    return _time_detalhe(db, usuario, times_svc.criar(db, usuario, pedido.nome, ip_do_pedido(request)))


@rotas.post("/times/{time_id}/membros", status_code=204)
def adicionar_ao_time(
    time_id: uuid.UUID, pedido: PedidoPessoa, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    times_svc.adicionar_membro(db, usuario, time_id, pedido.usuario_id, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.delete("/times/{time_id}/membros/{usuario_id}", status_code=204)
def tirar_do_time(
    time_id: uuid.UUID, usuario_id: uuid.UUID, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    times_svc.remover_membro(db, usuario, time_id, usuario_id, ip_do_pedido(request))
    return Response(status_code=204)


# --- Acesso de times ao espaço ----------------------------------------------------------------

@rotas.get("/espacos/{sigla}/times-acesso", response_model=list[AcessoTimeSaida])
def times_com_acesso(sigla: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[AcessoTimeSaida]:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    return [AcessoTimeSaida(time_id=t.id, nome=t.nome, papel=a.papel, membros=len(times_svc.membros(db, t)))
            for a, t in acesso.acessos_de_time(db, espaco)]


@rotas.post("/espacos/{sigla}/times-acesso", status_code=204)
def dar_acesso_time(
    sigla: str, pedido: PedidoTimeAcesso, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    acesso.dar_acesso_time(db, usuario, espaco, pedido.time_id, pedido.papel, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.patch("/espacos/{sigla}/times-acesso/{time_id}", status_code=204)
def mudar_acesso_time(
    sigla: str, time_id: uuid.UUID, pedido: PedidoPapel, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    acesso.mudar_acesso_time(db, usuario, espaco, time_id, pedido.papel, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.delete("/espacos/{sigla}/times-acesso/{time_id}", status_code=204)
def tirar_acesso_time(
    sigla: str, time_id: uuid.UUID, request: Request, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    acesso.tirar_acesso_time(db, usuario, espaco, time_id, ip_do_pedido(request))
    return Response(status_code=204)


# --- Gestor, suporte e espaço aberto ----------------------------------------------------------

@rotas.put("/espacos/{sigla}/acompanhar", status_code=204)
def acompanhar(sigla: str, pedido: PedidoSim, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> Response:
    acesso.acompanhar(db, usuario, espacos_svc.buscar_espaco(db, usuario, sigla), pedido.sim)
    return Response(status_code=204)


@rotas.get("/espacos/{sigla}/gestores", response_model=list[GestorSaida])
def gestores(sigla: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[GestorSaida]:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    return [GestorSaida(pessoa=PessoaResumo.de(u), desde=g.desde) for u, g in acesso.gestores_do_espaco(db, usuario, espaco)]


@rotas.post("/espacos/{sigla}/suporte", status_code=204)
def entrar_suporte(
    sigla: str, pedido: PedidoMotivo, request: Request, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    acesso.entrar_suporte(db, usuario, _espaco_bruto(db, sigla), pedido.motivo, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.delete("/espacos/{sigla}/suporte", status_code=204)
def sair_suporte(sigla: str, request: Request, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> Response:
    acesso.sair_suporte(db, usuario, _espaco_bruto(db, sigla), ip_do_pedido(request))
    return Response(status_code=204)


@rotas.put("/espacos/{sigla}/aberto", status_code=204)
def marcar_aberto(
    sigla: str, pedido: PedidoAberto, request: Request, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    acesso.marcar_aberto(db, usuario, espacos_svc.buscar_espaco(db, usuario, sigla), pedido.aberto, ip_do_pedido(request))
    return Response(status_code=204)


# --- Solicitar acesso -------------------------------------------------------------------------

@rotas.post("/espacos/{sigla}/solicitar-acesso", status_code=204)
def solicitar_no_espaco(
    sigla: str, pedido: PedidoMensagem, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)  # pelo espaço: quem já vê (Leitor ou espaço aberto)
    acesso.solicitar(db, usuario, espaco, None, pedido.mensagem)
    return Response(status_code=204)


@rotas.post("/itens/{chave}/solicitar-acesso", status_code=204)
def solicitar_pelo_item(
    chave: str, pedido: PedidoMensagem, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    """Botão Solicitar acesso de um item com "acesso restrito" (visto nos itens relacionados)."""
    achado = itens_svc.localizar(db, chave)
    if achado is None:
        raise HTTPException(status_code=404, detail="Item não encontrado.")
    item, espaco = achado
    acesso.solicitar(db, usuario, espaco, itens_svc.chave(espaco, item), pedido.mensagem)
    return Response(status_code=204)


@rotas.get("/espacos/{sigla}/pedidos", response_model=list[PedidoSaida])
def pedidos(sigla: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[PedidoSaida]:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla)
    return [PedidoSaida(id=p.id, pessoa=PessoaResumo.de(db.get(Usuario, p.usuario_id)), item_chave=p.item_chave,
                        mensagem=p.mensagem, criado_em=p.criado_em) for p in acesso.pedidos_pendentes(db, usuario, espaco)]


@rotas.post("/espacos/{sigla}/pedidos/{pedido_id}/aprovar", status_code=204)
def aprovar(
    sigla: str, pedido_id: uuid.UUID, pedido: PedidoPapel, request: Request,
    usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db),
) -> Response:
    acesso.aprovar(db, usuario, espacos_svc.buscar_espaco(db, usuario, sigla), pedido_id, pedido.papel, ip_do_pedido(request))
    return Response(status_code=204)


@rotas.post("/espacos/{sigla}/pedidos/{pedido_id}/recusar", status_code=204)
def recusar(
    sigla: str, pedido_id: uuid.UUID, request: Request, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)
) -> Response:
    acesso.recusar(db, usuario, espacos_svc.buscar_espaco(db, usuario, sigla), pedido_id, ip_do_pedido(request))
    return Response(status_code=204)


# --- Compartilhamento do espaço pessoal -------------------------------------------------------

@rotas.get("/espacos/{sigla}/compartilhamentos", response_model=list[PessoaResumo])
def compartilhamentos(sigla: str, usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[PessoaResumo]:
    espaco = espacos_svc.buscar_espaco(db, usuario, sigla, "compartilhar")
    return [PessoaResumo.de(u) for u, _ in acesso.compartilhamentos(db, espaco)]


@rotas.post("/espacos/{sigla}/compartilhamentos", status_code=204)
def compartilhar(sigla: str, pedido: PedidoPessoa, usuario: Usuario = Depends(usuario_atual),
                 db: Session = Depends(obter_db)) -> Response:
    acesso.compartilhar(db, usuario, espacos_svc.buscar_espaco(db, usuario, sigla), pedido.usuario_id)
    return Response(status_code=204)


@rotas.delete("/espacos/{sigla}/compartilhamentos/{usuario_id}", status_code=204)
def descompartilhar(sigla: str, usuario_id: uuid.UUID, usuario: Usuario = Depends(usuario_atual),
                    db: Session = Depends(obter_db)) -> Response:
    acesso.descompartilhar(db, usuario, espacos_svc.buscar_espaco(db, usuario, sigla), usuario_id)
    return Response(status_code=204)


# --- Explorar ---------------------------------------------------------------------------------

@rotas.get("/explorar", response_model=list[EspacoExplorar])
def explorar(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(obter_db)) -> list[EspacoExplorar]:
    """Espaços de equipe que a pessoa pode descobrir: os abertos (todos), e todos os de equipe para o Gestor
    e para o ADM da plataforma (que entra para suporte). Espaços pessoais nunca aparecem."""
    papeis = papeis_ativos(db, usuario.id)
    ve_todos = bool(papeis & {ADM, GESTOR})
    consulta = select(Espaco).where(Espaco.tipo == "projeto").order_by(Espaco.nome)
    if not ve_todos:
        consulta = consulta.where(Espaco.aberto)
    em_suporte = set(acesso.espacos_em_suporte(db, usuario))
    return [
        EspacoExplorar(sigla=e.sigla, nome=e.nome, aberto=e.aberto, meu_papel=espacos_svc.papel_no_espaco(db, usuario, e),
                       acompanha=acesso.acompanha(db, usuario, e), em_suporte=e.id in em_suporte)
        for e in db.scalars(consulta)
    ]
