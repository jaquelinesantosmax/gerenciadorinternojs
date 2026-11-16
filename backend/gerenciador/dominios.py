"""Domínios de e-mail autorizados a entrar. Só o ADM da plataforma configura."""

import re

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from . import relogio
from .auditoria import TipoEvento, registrar
from .erros import NaoEncontrado, OperacaoNegada
from .modelos import DominioAutorizado, Sessao, Usuario
from .papeis import exigir

DOMINIOS_INICIAIS = ("jusbrasil.com.br", "digesto.com.br")
_FORMATO = re.compile(r"^(?=.{3,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")


def listar(db: Session) -> list[DominioAutorizado]:
    return list(db.scalars(select(DominioAutorizado).order_by(DominioAutorizado.dominio)))


def adicionar(db: Session, ator: Usuario, dominio: str, ip: str | None) -> DominioAutorizado:
    exigir(db, ator, "configurar_dominios")
    dominio = dominio.strip().lower().lstrip("@")
    if not _FORMATO.match(dominio):
        raise OperacaoNegada("Informe um domínio válido, como jusbrasil.com.br.")
    if db.get(DominioAutorizado, dominio) is not None:
        raise OperacaoNegada(f"O domínio {dominio} já está autorizado.")
    novo = DominioAutorizado(dominio=dominio, adicionado_por_id=ator.id, adicionado_em=relogio.agora())
    db.add(novo)
    registrar(db, TipoEvento.DOMINIO_ADICIONADO, ator_id=ator.id, ip=ip, dominio=dominio)
    db.commit()
    return novo


def remover(db: Session, ator: Usuario, dominio: str, ip: str | None) -> None:
    exigir(db, ator, "configurar_dominios")
    dominio = dominio.strip().lower()
    existente = db.get(DominioAutorizado, dominio)
    if existente is None:
        raise NaoEncontrado("Domínio não encontrado.")
    if db.scalar(select(func.count()).select_from(DominioAutorizado)) <= 1:
        raise OperacaoNegada("Pelo menos um domínio precisa continuar autorizado.")
    if ator.email.endswith("@" + dominio):
        raise OperacaoNegada("Você não pode remover o domínio do seu próprio e-mail.")
    db.delete(existente)
    # Quem é do domínio removido sai na hora, como na desativação.
    encerradas = db.execute(
        update(Sessao)
        .where(
            Sessao.encerrada_em.is_(None),
            Sessao.usuario_id.in_(select(Usuario.id).where(Usuario.email.endswith("@" + dominio))),
        )
        .values(encerrada_em=relogio.agora(), motivo_encerramento="dominio_removido")
    ).rowcount or 0
    registrar(db, TipoEvento.DOMINIO_REMOVIDO, ator_id=ator.id, ip=ip, dominio=dominio,
              sessoes_encerradas=encerradas)
    db.commit()
