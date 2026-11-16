"""Times (Etapa 4): lista única para toda a ferramenta, com membros. Também alimenta o campo Time dos itens.

- Criam times: ADM da plataforma, Gestor, quem pode criar espaços e quem é ADM de algum espaço.
- Editam ou excluem: quem criou, o Gestor e o ADM da plataforma.
- Quem entra ou sai do time ganha ou perde, na hora, o acesso que o time tem aos espaços.
"""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import relogio
from .auditoria import TipoEvento, registrar
from .erros import NaoEncontrado, OperacaoNegada, SemPermissao
from .modelos import Usuario
from .modelos_acesso import MembroTime
from .modelos_espacos import MembroEspaco, TimeProvisorio
from .papeis import ADM, GESTOR, pode


def listar(db: Session, incluir_inativos: bool = False) -> list[TimeProvisorio]:
    consulta = select(TimeProvisorio).order_by(TimeProvisorio.nome)
    if not incluir_inativos:
        consulta = consulta.where(TimeProvisorio.ativo)
    return list(db.scalars(consulta))


def pode_criar(db: Session, usuario: Usuario) -> bool:
    if pode(db, usuario, "criar_time"):
        return True
    return db.scalar(select(MembroEspaco.id).where(MembroEspaco.usuario_id == usuario.id, MembroEspaco.papel == "adm")) is not None


def pode_editar(db: Session, usuario: Usuario, time: TimeProvisorio) -> bool:
    from .papeis import papeis_ativos

    return usuario.ativo and (time.criado_por_id == usuario.id or bool(papeis_ativos(db, usuario.id) & {ADM, GESTOR}))


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
    if not pode_criar(db, ator):
        raise SemPermissao("Você não tem permissão para criar times.")
    time = TimeProvisorio(nome=_nome(db, nome), ativo=True, criado_em=relogio.agora(), criado_por_id=ator.id)
    db.add(time)
    registrar(db, TipoEvento.TIME_CRIADO, ator_id=ator.id, ip=ip, time=time.nome)
    db.commit()
    return time


def buscar(db: Session, time_id: uuid.UUID) -> TimeProvisorio:
    time = db.get(TimeProvisorio, time_id)
    if time is None:
        raise NaoEncontrado("Time não encontrado.")
    return time


def _exigir_editar(db: Session, ator: Usuario, time: TimeProvisorio) -> None:
    if not pode_editar(db, ator, time):
        raise SemPermissao("Só quem criou o time, o Gestor e o ADM da plataforma podem mudá-lo.")


def alterar(db: Session, ator: Usuario, time_id: uuid.UUID, nome: str | None, ativo: bool | None) -> None:
    """Renomear ou desativar. Time desativado sai da lista de escolha e deixa de dar acesso, mas continua nos itens."""
    time = buscar(db, time_id)
    _exigir_editar(db, ator, time)
    if nome is not None:
        time.nome = _nome(db, nome, ignorar=time.id)
    if ativo is not None:
        time.ativo = ativo
    db.commit()


def membros(db: Session, time: TimeProvisorio) -> list[Usuario]:
    return list(db.scalars(select(Usuario).join(MembroTime, MembroTime.usuario_id == Usuario.id)
                           .where(MembroTime.time_id == time.id).order_by(Usuario.nome)))


def adicionar_membro(db: Session, ator: Usuario, time_id: uuid.UUID, usuario_id: uuid.UUID, ip: str | None) -> None:
    time = buscar(db, time_id)
    _exigir_editar(db, ator, time)
    alvo = db.get(Usuario, usuario_id)
    if alvo is None or not alvo.ativo:
        raise NaoEncontrado("Pessoa não encontrada.")
    if db.get(MembroTime, (time.id, alvo.id)) is not None:
        raise OperacaoNegada(f"{alvo.nome} já está no time {time.nome}.")
    db.add(MembroTime(time_id=time.id, usuario_id=alvo.id, adicionado_em=relogio.agora()))
    registrar(db, TipoEvento.TIME_MEMBRO_ADICIONADO, ator_id=ator.id, alvo_usuario_id=alvo.id, ip=ip, time=time.nome)
    db.commit()


def remover_membro(db: Session, ator: Usuario, time_id: uuid.UUID, usuario_id: uuid.UUID, ip: str | None) -> None:
    time = buscar(db, time_id)
    _exigir_editar(db, ator, time)
    membro = db.get(MembroTime, (time.id, usuario_id))
    if membro is None:
        raise NaoEncontrado("Essa pessoa não está no time.")
    db.delete(membro)
    registrar(db, TipoEvento.TIME_MEMBRO_REMOVIDO, ator_id=ator.id, alvo_usuario_id=usuario_id, ip=ip, time=time.nome)
    db.commit()
