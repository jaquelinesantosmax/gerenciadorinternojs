"""Tabelas da Etapa 4: membros de times, acesso de times a espaços, Gestores que acompanham espaços,
suporte do ADM da plataforma, pedidos de acesso e compartilhamento do espaço pessoal."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .banco import Base


class MembroTime(Base):
    __tablename__ = "membros_time"

    time_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("times.id", ondelete="CASCADE"), primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), primary_key=True, index=True)
    adicionado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AcessoTime(Base):
    """Acesso de um time inteiro a um espaço: quem entra ou sai do time ganha ou perde o acesso."""

    __tablename__ = "acessos_time"
    __table_args__ = (UniqueConstraint("espaco_id", "time_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    time_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("times.id", ondelete="CASCADE"), index=True)
    papel: Mapped[str] = mapped_column(String(16))
    adicionado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    adicionado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GestorAcompanha(Base):
    """Espaços que um Gestor escolheu acompanhar (vão para o Espaço da Gestão)."""

    __tablename__ = "gestores_acompanham"
    __table_args__ = (UniqueConstraint("usuario_id", "espaco_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    desde: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SessaoSuporte(Base):
    """Entrada do ADM da plataforma num espaço de equipe, com motivo e prazo (decisão de 16/11: 4 horas)."""

    __tablename__ = "sessoes_suporte"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    motivo: Mapped[str] = mapped_column(Text)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    encerrada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PedidoAcesso(Base):
    """Pedido feito pelo botão Solicitar acesso. Os ADMs do espaço aprovam escolhendo o papel."""

    __tablename__ = "pedidos_acesso"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    # Item que motivou o pedido (link "acesso restrito"), se houver.
    item_chave: Mapped[str | None] = mapped_column(String(24))
    mensagem: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(String(16), default="pendente")
    decidido_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    decidido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    papel: Mapped[str | None] = mapped_column(String(16))


class Compartilhamento(Base):
    """Espaço pessoal compartilhado com uma pessoa: sempre só leitura (decisão de 16/11)."""

    __tablename__ = "compartilhamentos"
    __table_args__ = (UniqueConstraint("espaco_id", "usuario_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
