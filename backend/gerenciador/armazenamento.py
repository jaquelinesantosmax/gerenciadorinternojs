"""Onde os arquivos dos anexos ficam guardados.

O resto do sistema só conversa com a interface Armazenamento. Hoje os arquivos ficam numa pasta do
computador; quando a hospedagem for decidida, basta criar outra implementação (por exemplo, Cloud Storage)
sem mexer nas regras de anexos.
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import BinaryIO, Protocol

from .config import obter_config


class ArquivoGrandeDemais(Exception):
    pass


class Armazenamento(Protocol):
    def salvar(self, origem: BinaryIO, limite_bytes: int) -> tuple[str, int]:
        """Guarda o conteúdo e devolve (chave, tamanho). Interrompe se passar do limite."""

    def ler(self, chave: str) -> Iterator[bytes]: ...

    def primeiros_bytes(self, chave: str, quantidade: int) -> bytes: ...

    def apagar(self, chave: str) -> None: ...


class ArmazenamentoLocal:
    BLOCO = 1024 * 1024

    def __init__(self, pasta: str):
        self.pasta = Path(pasta)

    def _caminho(self, chave: str) -> Path:
        # A chave é sempre gerada aqui (dois níveis de pasta + uuid); nunca vem de fora.
        caminho = (self.pasta / chave).resolve()
        if self.pasta.resolve() not in caminho.parents:
            raise ValueError("chave inválida")
        return caminho

    def salvar(self, origem: BinaryIO, limite_bytes: int) -> tuple[str, int]:
        nome = uuid.uuid4().hex
        chave = f"{nome[:2]}/{nome}"
        destino = self._caminho(chave)
        destino.parent.mkdir(parents=True, exist_ok=True)
        tamanho = 0
        try:
            with open(destino, "wb") as saida:
                while bloco := origem.read(self.BLOCO):
                    tamanho += len(bloco)
                    if tamanho > limite_bytes:
                        raise ArquivoGrandeDemais()
                    saida.write(bloco)
        except BaseException:
            destino.unlink(missing_ok=True)
            raise
        return chave, tamanho

    def ler(self, chave: str) -> Iterator[bytes]:
        with open(self._caminho(chave), "rb") as arquivo:
            while bloco := arquivo.read(self.BLOCO):
                yield bloco

    def primeiros_bytes(self, chave: str, quantidade: int) -> bytes:
        with open(self._caminho(chave), "rb") as arquivo:
            return arquivo.read(quantidade)

    def apagar(self, chave: str) -> None:
        try:
            os.remove(self._caminho(chave))
        except FileNotFoundError:
            pass


def obter_armazenamento() -> Armazenamento:
    return ArmazenamentoLocal(obter_config().pasta_anexos)
