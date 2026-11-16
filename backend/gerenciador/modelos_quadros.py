"""Tabelas da Etapa 3a: status ligados em cada espaço, transições do workflow, quadros e colunas."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .banco import Base

TIPOS_QUADRO = ("kanban", "simples", "scrum")


class StatusDoEspaco(Base):
    """Quais status (padrão ou próprios) estão ligados num espaço, e em que ordem."""

    __tablename__ = "status_do_espaco"
    __table_args__ = (UniqueConstraint("espaco_id", "status_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    status_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("status_item.id", ondelete="CASCADE"))
    ordem: Mapped[int] = mapped_column(Integer)


class Transicao(Base):
    """Passagem permitida de um status para outro, no workflow de um espaço."""

    __tablename__ = "transicoes"
    __table_args__ = (UniqueConstraint("espaco_id", "de_status_id", "para_status_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    de_status_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("status_item.id", ondelete="CASCADE"))
    para_status_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("status_item.id", ondelete="CASCADE"))


class Quadro(Base):
    """Quadro sobre os itens de um espaço (ou de um painel). Um espaço pode ter vários."""

    __tablename__ = "quadros"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    # Preenchido quando o quadro é o de um painel (cada painel tem quadro e colunas próprios).
    painel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("paineis.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    tipo: Mapped[str] = mapped_column(String(16))
    # Kanban: itens em Backlog ficam numa área separada, fora do quadro (decisão de 16/11).
    usa_backlog: Mapped[bool] = mapped_column(Boolean, default=False)
    # Scrum: unidade da estimativa (pontos, horas ou contagem de itens), escolhida por quadro.
    unidade_estimativa: Mapped[str] = mapped_column(String(16), default="pontos", server_default="pontos")
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ColunaQuadro(Base):
    """Coluna de um quadro. Não é status: uma coluna pode juntar vários status."""

    __tablename__ = "colunas_quadro"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quadro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quadros.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(80))
    ordem: Mapped[int] = mapped_column(Integer)
    # Limite de itens na coluna (Kanban). Passar do limite gera alerta, não bloqueia.
    limite: Mapped[int | None] = mapped_column(Integer)
    status_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
