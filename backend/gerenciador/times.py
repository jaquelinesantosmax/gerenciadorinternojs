"""Lista provisória de Times (decisão de 16/11), mantida pelo ADM da plataforma até a Etapa 4."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import relogio
from .auditoria import TipoEvento, registrar
from .erros import NaoEncontrado, OperacaoNegada
from .modelos import Usuario
from .modelos_espacos import TimeProvisorio
from .papeis import exigir


def listar(db: Session, incluir_inativos: bool = False) -> list[TimeProvisorio]:
    consulta = select(TimeProvisorio).order_by(TimeProvisorio.nome)
    if not incluir_inativos:
        consulta = consulta.where(TimeProvisorio.ativo)
    return list(db.scalars(consulta))


def _nome(db: Session, nome: str, ignorar: uuid.UUID | None = None) -> str:
    nome = nome.strip()
    if not nome:
        raise OperacaoNegada("Informe o nome do time.")
    if len(nome) > 120:
        raise OperacaoNegada("O nome pode ter até 120 caracteres.")
    existente = db.scalar(select(TimeProvisorio).where(func.lower(TimeProvisorio.nome) == nome.lower()))
    if existente is not None and existente.id != ignorar:
        raise OperacaoNegada(f"Já existe um time chamado {existente.nome}.")
    return nome


def criar(db: Session, ator: Usuario, nome: str, ip: str | None) -> TimeProvisorio:
    exigir(db, ator, "gerenciar_times_provisorios")
    time = TimeProvisorio(nome=_nome(db, nome), ativo=True, criado_em=relogio.agora())
    db.add(time)
    registrar(db, TipoEvento.TIME_CRIADO, ator_id=ator.id, ip=ip, time=time.nome)
    db.commit()
    return time


def _buscar(db: Session, time_id: uuid.UUID) -> TimeProvisorio:
    time = db.get(TimeProvisorio, time_id)
    if time is None:
        raise NaoEncontrado("Time não encontrado.")
    return time


def alterar(db: Session, ator: Usuario, time_id: uuid.UUID, nome: str | None, ativo: bool | None) -> None:
    """Renomear ou tirar da lista de escolha. Um time desativado continua nos itens que já o usam."""
    exigir(db, ator, "gerenciar_times_provisorios")
    time = _buscar(db, time_id)
    if nome is not None:
        time.nome = _nome(db, nome, ignorar=time.id)
    if ativo is not None:
        time.ativo = ativo
    db.commit()
