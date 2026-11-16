"""Tabelas da Etapa 2, parte 1: espaços, membros, painéis, tipos de item, status, Times provisórios e origens."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .banco import Base
from .modelos import Usuario

# Tipos de espaço da Etapa 2. Service desk chega na Etapa 5.
TIPOS_ESPACO = ("projeto", "pessoal")
# Modelos escolhidos na criação. Ficam guardados e passam a valer na Etapa 3 (workflow e quadros).
MODELOS_PROJETO = ("scrum", "kanban", "gestao_tarefas")
PAPEIS_ESPACO = ("adm", "membro", "leitor")
# Níveis da hierarquia: Épico > História, Tarefa ou Bug (e tipos próprios) > Subtarefa.
NIVEIS_TIPO = ("epico", "padrao", "subtarefa")
CATEGORIAS_STATUS = ("a_fazer", "em_andamento", "concluido")


class TimeProvisorio(Base):
    """Lista provisória de Times (decisão de 16/11), mantida pelo ADM da plataforma até a Etapa 4."""

    __tablename__ = "times"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Quem criou o time pode editá-lo (além do Gestor e do ADM da plataforma). Vazio nos times da lista provisória.
    criado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))


class Espaco(Base):
    __tablename__ = "espacos"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Sigla de 2 a 10 letras maiúsculas, única e fixa (decisão de 16/11). Base das chaves dos itens.
    sigla: Mapped[str] = mapped_column(String(10), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str | None] = mapped_column(Text)
    tipo: Mapped[str] = mapped_column(String(16))
    modelo: Mapped[str | None] = mapped_column(String(32))
    # Espaço pessoal: o dono. Espaço de projeto: vazio (os ADMs estão em membros_espaco).
    dono_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # Espaço aberto: leitura, comentários e anexos para toda a empresa (marcado pelo ADM do espaço).
    aberto: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    # Próximo número para a chave dos itens (LOP-1, LOP-2...).
    proximo_numero: Mapped[int] = mapped_column(Integer, default=1)


class MembroEspaco(Base):
    __tablename__ = "membros_espaco"
    __table_args__ = (UniqueConstraint("espaco_id", "usuario_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"), index=True)
    papel: Mapped[str] = mapped_column(String(16))
    adicionado_por_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("usuarios.id"))
    adicionado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    usuario: Mapped[Usuario] = relationship(foreign_keys=[usuario_id], lazy="joined")


class Painel(Base):
    """Sub-espaço dentro de um espaço, como as frentes do JSOL. Não tem membros próprios."""

    __tablename__ = "paineis"
    __table_args__ = (UniqueConstraint("espaco_id", "nome"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    criado_por_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("usuarios.id"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TipoItem(Base):
    """Tipos de item. espaco_id vazio = tipo padrão da plataforma (Épico, História, Tarefa, Bug, Subtarefa)."""

    __tablename__ = "tipos_item"
    __table_args__ = (UniqueConstraint("espaco_id", "nome"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(60))
    nivel: Mapped[str] = mapped_column(String(16))
    ordem: Mapped[int] = mapped_column(Integer, default=100)


class StatusItem(Base):
    """Status. Na Etapa 2 só existem os 8 padrão da plataforma (espaco_id vazio)."""

    __tablename__ = "status_item"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(60))
    categoria: Mapped[str] = mapped_column(String(16))
    ordem: Mapped[int] = mapped_column(Integer)


class OpcaoOrigem(Base):
    """Opções do campo Origem da solicitação, mantidas pelo ADM de cada espaço (decisão de 16/11)."""

    __tablename__ = "opcoes_origem"
    __table_args__ = (UniqueConstraint("espaco_id", "nome"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    espaco_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("espacos.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
