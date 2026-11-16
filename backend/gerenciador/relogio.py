"""Hora atual em UTC. Fica num módulo próprio para os testes poderem simular a passagem do tempo."""

from datetime import UTC, datetime


def agora() -> datetime:
    return datetime.now(UTC)
