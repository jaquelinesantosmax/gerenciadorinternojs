"""Formatos das respostas e dos pedidos da API."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..modelos import Papel, Usuario


class PessoaResumo(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    foto_url: str | None = None

    @classmethod
    def de(cls, u: Usuario | None) -> "PessoaResumo | None":
        if u is None:
            return None
        return cls(id=u.id, nome=u.nome, email=u.email, foto_url=u.foto_url)


class Eu(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    foto_url: str | None
    papeis: list[Papel]
    permissoes: dict[str, bool]


class Provedores(BaseModel):
    teste: bool
    google: bool


class PedidoLoginTeste(BaseModel):
    email: str = Field(max_length=320)
    nome: str = Field(default="", max_length=200)


class UsuarioAdmin(BaseModel):
    id: uuid.UUID
    nome: str
    email: str
    foto_url: str | None
    ativo: bool
    papeis: list[Papel]
    criado_em: datetime
    ultimo_acesso_em: datetime | None
    desativado_em: datetime | None


class PedidoPapel(BaseModel):
    papel: Papel


class GestorItem(BaseModel):
    usuario: PessoaResumo
    concedido_por: PessoaResumo | None
    concedido_em: datetime


class EventoItem(BaseModel):
    id: int
    ocorrido_em: datetime
    tipo: str
    ator: PessoaResumo | None
    alvo: PessoaResumo | None
    detalhes: dict[str, Any]
    ip: str | None


class PaginaEventos(BaseModel):
    eventos: list[EventoItem]
    proximo: int | None


class DominioItem(BaseModel):
    dominio: str
    adicionado_por: PessoaResumo | None
    adicionado_em: datetime


class PedidoDominio(BaseModel):
    dominio: str = Field(max_length=253)
