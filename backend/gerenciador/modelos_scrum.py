"""Tabelas da Etapa 3b: sprints, itens das sprints e o registro de mudanças de status (base das métricas)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Identity, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .banco import Base

ESTADOS_SPRINT = ("planejada", "ativa", "encerrada")
UNIDADES_ESTIMATIVA = {"pontos": "Story points", "horas": "Horas", "itens": "Contagem de itens"}


class Sprint(Base):
    __tablename__ = "sprints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quadro_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quadros.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    objetivo: Mapped[str | None] = mapped_column(Text)
    inicio: Mapped[date | None] = mapped_column(Date)
    fim: Mapped[date | None] = mapped_column(Date)
    estado: Mapped[str] = mapped_column(String(16), default="planejada")
    iniciada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    encerrada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Fotografias para o relatório e a velocidade: o que foi assumido no início e o que foi entregue no fim.
    compromisso: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    entregue: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ItemDaSprint(Base):
    """Passagem de um item por uma sprint. Guardar entrada e saída permite medir escopo adicionado e o burndown."""

    __tablename__ = "itens_da_sprint"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sprint_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sprints.id", ondelete="CASCADE"), index=True)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens.id", ondelete="CASCADE"), index=True)
    adicionado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    removido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    adicionado_apos_inicio: Mapped[bool] = mapped_column(Boolean, default=False)
    # Preenchido ao encerrar: o item terminou a sprint concluído?
    concluido_na_sprint: Mapped[bool | None] = mapped_column(Boolean)


class MudancaStatus(Base):
    """Cada mudança de status, com a categoria de destino. Base do fluxo acumulado e do tempo de ciclo."""

    __tablename__ = "mudancas_status"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens.id", ondelete="CASCADE"), index=True)
    de_status_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("status_item.id", ondelete="SET NULL"))
    para_status_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("status_item.id", ondelete="SET NULL"))
    categoria: Mapped[str] = mapped_column(String(16))
    quando: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
