"""Sessões de login.

Decisão de 16/11: a sessão dura 15 dias e renova a cada uso; só cai depois de 15 dias seguidos sem uso.
"""

import hashlib
import secrets
import uuid
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from . import relogio
from .config import obter_config
from .modelos import Sessao, Usuario

NOME_COOKIE = "gerenciador_sessao"
# Evita gravar no banco a cada clique: a renovação só é gravada se o último uso tiver mais de 5 minutos.
INTERVALO_RENOVACAO = timedelta(minutes=5)


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def duracao() -> timedelta:
    return timedelta(days=obter_config().sessao_dias)


def criar(db: Session, usuario: Usuario, ip: str | None, agente: str | None) -> str:
    """Cria a sessão e devolve o token que vai no cookie. O token em si nunca é guardado."""
    token = secrets.token_urlsafe(32)
    agora = relogio.agora()
    db.add(
        Sessao(
            usuario_id=usuario.id,
            token_hash=_hash(token),
            criada_em=agora,
            ultimo_uso_em=agora,
            expira_em=agora + duracao(),
            ip=ip,
            agente=(agente or "")[:400] or None,
        )
    )
    return token


def validar(db: Session, token: str | None) -> tuple[Sessao | None, bool]:
    """Devolve (sessão, renovada). A sessão é None se não existir, tiver expirado ou sido encerrada,
    ou se o usuário estiver desativado. "renovada" indica que o cookie precisa ser regravado."""
    if not token:
        return None, False
    sessao = db.scalar(select(Sessao).where(Sessao.token_hash == _hash(token)))
    agora = relogio.agora()
    if sessao is None or sessao.encerrada_em is not None or sessao.expira_em <= agora:
        return None, False
    if not sessao.usuario.ativo:
        return None, False
    if agora - sessao.ultimo_uso_em >= INTERVALO_RENOVACAO:
        sessao.ultimo_uso_em = agora
        sessao.expira_em = agora + duracao()
        sessao.usuario.ultimo_acesso_em = agora
        return sessao, True
    return sessao, False


def encerrar(db: Session, sessao: Sessao, motivo: str) -> None:
    sessao.encerrada_em = relogio.agora()
    sessao.motivo_encerramento = motivo


def encerrar_todas(db: Session, usuario_id: uuid.UUID, motivo: str) -> int:
    """Encerra todas as sessões abertas do usuário na hora. Devolve quantas foram encerradas."""
    resultado = db.execute(
        update(Sessao)
        .where(Sessao.usuario_id == usuario_id, Sessao.encerrada_em.is_(None))
        .values(encerrada_em=relogio.agora(), motivo_encerramento=motivo)
    )
    return resultado.rowcount or 0
