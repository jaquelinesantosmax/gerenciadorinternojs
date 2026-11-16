"""Desativação e reativação de usuários pelo ADM da plataforma."""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import relogio, sessoes
from .auditoria import TipoEvento, registrar
from .erros import NaoEncontrado, OperacaoNegada
from .modelos import Usuario
from .papeis import ADM, contar_adms_ativos, exigir, papeis_ativos


def _buscar(db: Session, usuario_id: uuid.UUID) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise NaoEncontrado("Usuário não encontrado.")
    return usuario


def desativar(db: Session, ator: Usuario, alvo_id: uuid.UUID, ip: str | None) -> None:
    """Desativa e encerra todas as sessões do usuário na hora. Papéis e acessos ficam guardados."""
    exigir(db, ator, "desativar_usuarios")
    alvo = _buscar(db, alvo_id)
    if alvo.id == ator.id:
        raise OperacaoNegada("Você não pode desativar o seu próprio usuário.")
    if not alvo.ativo:
        raise OperacaoNegada(f"{alvo.nome} já está desativado.")
    if ADM in papeis_ativos(db, alvo.id) and contar_adms_ativos(db) <= 1:
        raise OperacaoNegada("A plataforma precisa ter pelo menos um ADM da plataforma ativo.")
    alvo.ativo = False
    alvo.desativado_em = relogio.agora()
    alvo.desativado_por_id = ator.id
    encerradas = sessoes.encerrar_todas(db, alvo.id, "usuario_desativado")
    registrar(db, TipoEvento.USUARIO_DESATIVADO, ator_id=ator.id, alvo_usuario_id=alvo.id, ip=ip,
              sessoes_encerradas=encerradas)
    db.commit()


def reativar(db: Session, ator: Usuario, alvo_id: uuid.UUID, ip: str | None) -> None:
    """Decisão de 16/11: a pessoa volta com os mesmos papéis e acessos que tinha."""
    exigir(db, ator, "desativar_usuarios")
    alvo = _buscar(db, alvo_id)
    if alvo.ativo:
        raise OperacaoNegada(f"{alvo.nome} já está ativo.")
    alvo.ativo = True
    alvo.desativado_em = None
    alvo.desativado_por_id = None
    registrar(db, TipoEvento.USUARIO_REATIVADO, ator_id=ator.id, alvo_usuario_id=alvo.id, ip=ip)
    db.commit()


def listar(db: Session, ator: Usuario, busca: str | None = None) -> list[Usuario]:
    exigir(db, ator, "ver_usuarios")
    consulta = select(Usuario).order_by(Usuario.nome)
    if busca and busca.strip():
        termo = f"%{busca.strip().lower()}%"
        consulta = consulta.where(or_(Usuario.email.like(termo), Usuario.nome.ilike(termo)))
    return list(db.scalars(consulta))
