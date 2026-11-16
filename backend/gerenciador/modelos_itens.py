"""Tabelas da Etapa 2, partes 2 e 3: itens, campos personalizados, histórico, comentários, anexos e vínculos."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .banco import Base

# Decisão de 16/11.
PRIORIDADES = {"critica": "Crítica", "alta": "Alta", "media": "Média", "baixa": "Baixa"}

TIPOS_CAMPO = {
    "texto_curto": "Texto curto",
    "texto_longo": "Texto longo",
    "numero": "Número",
    "moeda": "Moeda",
    "data": "Data",
    "data_hora": "Data e hora",
    "url": "URL",
    "lista_unica": "Lista de escolha única",
    "lista_multipla": "Lista de escolha múltipla",
    "lista_cascata": "Lista em cascata",
    "pessoa": "Pessoa",
    "sim_nao": "Sim/Não",
}

# Sete tipos fixos de vínculo (docs/decisoes-de-desenho.md): (nome de quem aponta, nome do outro lado).
TIPOS_VINCULO = {
    "bloqueia": ("bloqueia", "é bloqueado por"),
    "relacionado": ("relacionado a", "relacionado a"),
    "duplica": ("duplica", "é duplicado por"),
    "clona": ("clona", "é clonado de"),
    "causa": ("causa", "é causado por"),
    "dividido": ("dividido em", "dividido de"),
    "escalado": ("escalado para", "é escalação de"),
}


class Item(Base):
    __tablename__ = "itens"
    __table_args__ = (UniqueConstraint("espaco_id", "numero"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id"), index=True)
    numero: Mapped[int] = mapped_column(Integer)
    tipo_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tipos_item.id"), index=True)
    resumo: Mapped[str] = mapped_column(String(255))
    # Texto formatado guardado como documento (formato do editor), nunca como HTML solto.
    descricao: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("status_item.id"))
    prioridade: Mapped[str] = mapped_column(String(16))
    responsavel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    relator_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    time_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("times.id"))
    data_inicio: Mapped[date] = mapped_column(Date)
    data_entrega: Mapped[date] = mapped_column(Date)
    data_real_entrega: Mapped[date | None] = mapped_column(Date)
    justificativa_atraso: Mapped[str | None] = mapped_column(Text)
    estimativa: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    # Decisão de 16/11: estimativa em horas separada dos story points.
    estimativa_horas: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    pai_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("itens.id"), index=True)
    painel_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("paineis.id"), index=True)
    origem_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("opcoes_origem.id"))
    categorias: Mapped[list[str]] = mapped_column(ARRAY(String(60)), default=list, server_default=text("'{}'"))
    # Valores dos campos personalizados: {id do campo: valor}.
    valores: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    excluido_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))


class CoResponsavel(Base):
    __tablename__ = "co_responsaveis"

    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens.id", ondelete="CASCADE"), primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), primary_key=True)


class ApelidoItem(Base):
    """Chave antiga de um item que mudou de espaço, para não quebrar vínculos com o GitHub."""

    __tablename__ = "apelidos_item"

    chave: Mapped[str] = mapped_column(String(24), primary_key=True)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens.id", ondelete="CASCADE"), index=True)


class CampoPersonalizado(Base):
    __tablename__ = "campos_personalizados"
    __table_args__ = (UniqueConstraint("espaco_id", "nome"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(80))
    tipo: Mapped[str] = mapped_column(String(24))
    obrigatorio: Mapped[bool] = mapped_column(Boolean, default=False)
    # Tipos de item em que o campo aparece (decisão de 16/11).
    tipos_item: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    # Opções das listas, moeda, se aceita várias pessoas etc.
    config: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    ordem: Mapped[int] = mapped_column(Integer, default=0)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class HistoricoItem(Base):
    """Cada alteração do item: quem, quando, valor anterior e novo."""

    __tablename__ = "historico_item"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens.id", ondelete="CASCADE"), index=True)
    autor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    ocorrido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    campo: Mapped[str] = mapped_column(String(80))
    valor_anterior: Mapped[str | None] = mapped_column(Text)
    valor_novo: Mapped[str | None] = mapped_column(Text)


class Comentario(Base):
    __tablename__ = "comentarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens.id", ondelete="CASCADE"), index=True)
    autor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    corpo: Mapped[dict[str, Any]] = mapped_column(JSONB)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    editado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    excluido_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))


class VersaoComentario(Base):
    """Versão anterior de um comentário editado (fica no histórico)."""

    __tablename__ = "versoes_comentario"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    comentario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comentarios.id", ondelete="CASCADE"), index=True)
    corpo: Mapped[dict[str, Any]] = mapped_column(JSONB)
    substituido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Anexo(Base):
    __tablename__ = "anexos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens.id", ondelete="CASCADE"), index=True)
    nome_arquivo: Mapped[str] = mapped_column(String(255))
    tipo_mime: Mapped[str] = mapped_column(String(160))
    tamanho: Mapped[int] = mapped_column(BigInteger)
    # Onde o arquivo está guardado, no formato do armazenamento em uso (trocável).
    chave_armazenamento: Mapped[str] = mapped_column(String(300))
    enviado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    enviado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    excluido_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))


class Vinculo(Base):
    """Vínculo entre itens. Guardado uma vez, na direção de quem aponta; o outro lado é mostrado com o nome inverso."""

    __tablename__ = "vinculos"
    __table_args__ = (UniqueConstraint("tipo", "origem_id", "destino_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tipo: Mapped[str] = mapped_column(String(16))
    origem_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens.id", ondelete="CASCADE"), index=True)
    destino_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("itens.id", ondelete="CASCADE"), index=True)
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ConfigPlataforma(Base):
    """Ajustes da plataforma (ex.: limite de anexos)."""

    __tablename__ = "config_plataforma"

    chave: Mapped[str] = mapped_column(String(60), primary_key=True)
    valor: Mapped[Any] = mapped_column(JSONB)
