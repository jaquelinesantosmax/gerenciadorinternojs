"""Tabelas do banco da Etapa 1: usuários, papéis da plataforma, sessões, domínios e auditoria."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Identity, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .banco import Base


class Papel(str, enum.Enum):
    """Papéis que valem para a plataforma inteira (docs/matriz-de-permissoes.md, seção Plataforma)."""

    ADM_PLATAFORMA = "adm_plataforma"
    GESTOR = "gestor"
    CRIAR_ESPACOS = "criar_espacos"


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Sempre guardado em minúsculas.
    email: Mapped[str] = mapped_column(String(320), unique=True)
    nome: Mapped[str] = mapped_column(String(200))
    foto_url: Mapped[str | None] = mapped_column(Text)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultimo_acesso_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    desativado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    desativado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))


class ConcessaoPapel(Base):
    """Cada vez que um papel é dado. Fica ativo enquanto revogado_em estiver vazio.

    Guardar o histórico permite mostrar quem concedeu e quando (lista de Gestores).
    """

    __tablename__ = "concessoes_papel"
    __table_args__ = (
        Index(
            "uq_concessao_ativa",
            "usuario_id",
            "papel",
            unique=True,
            postgresql_where=text("revogado_em IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    papel: Mapped[str] = mapped_column(String(32))
    # Vazio quando o papel foi dado na instalação.
    concedido_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    concedido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revogado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    revogado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id])
    concedido_por: Mapped[Usuario | None] = relationship(foreign_keys=[concedido_por_id])


class Sessao(Base):
    __tablename__ = "sessoes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    # O cookie guarda o token; o banco guarda só o hash, para um vazamento do banco não abrir sessões.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultimo_uso_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    encerrada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_encerramento: Mapped[str | None] = mapped_column(String(32))
    ip: Mapped[str | None] = mapped_column(String(64))
    agente: Mapped[str | None] = mapped_column(String(400))

    usuario: Mapped[Usuario] = relationship(lazy="joined")


class DominioAutorizado(Base):
    __tablename__ = "dominios_autorizados"

    dominio: Mapped[str] = mapped_column(String(253), primary_key=True)
    adicionado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    adicionado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EventoAuditoria(Base):
    __tablename__ = "eventos_auditoria"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    tipo: Mapped[str] = mapped_column(String(48), index=True)
    ator_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    alvo_usuario_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"), index=True)
    detalhes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    ip: Mapped[str | None] = mapped_column(String(64))

    ator: Mapped[Usuario | None] = relationship(foreign_keys=[ator_id], lazy="joined")
    alvo: Mapped[Usuario | None] = relationship(foreign_keys=[alvo_usuario_id], lazy="joined")


# Tabelas das etapas seguintes (importadas aqui para todas ficarem registradas juntas).
from . import (
    modelos_espacos,  # noqa: E402, F401
    modelos_itens,  # noqa: E402, F401
    modelos_quadros,  # noqa: E402, F401
)
