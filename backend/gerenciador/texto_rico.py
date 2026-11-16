"""Texto formatado da descrição e dos comentários.

O texto é guardado como documento do editor (JSON), nunca como HTML. Aqui o documento é conferido
antes de ser salvo: só entram os elementos permitidos, links só com http, https ou mailto, e imagens
só de anexos do próprio item. Assim ninguém consegue esconder código no texto.
"""

import json
import re
import uuid
from typing import Any

from .erros import ErroDeRegra

NOS_PERMITIDOS = {
    "doc", "paragraph", "text", "heading", "bulletList", "orderedList", "listItem", "blockquote",
    "codeBlock", "hardBreak", "horizontalRule", "table", "tableRow", "tableHeader", "tableCell",
    "image", "mention",
}
MARCAS_PERMITIDAS = {"bold", "italic", "strike", "code", "link"}
_ESQUEMAS_LINK = re.compile(r"^(https?://|mailto:)", re.IGNORECASE)
TAMANHO_MAXIMO = 300_000  # caracteres do documento em JSON
PROFUNDIDADE_MAXIMA = 30


def _erro() -> ErroDeRegra:
    return ErroDeRegra("O texto tem um formato que não é aceito.")


def _conferir(no: Any, profundidade: int, anexos: set[uuid.UUID] | None) -> None:
    if profundidade > PROFUNDIDADE_MAXIMA or not isinstance(no, dict):
        raise _erro()
    tipo = no.get("type")
    if tipo not in NOS_PERMITIDOS:
        raise _erro()
    if tipo == "text" and not isinstance(no.get("text"), str):
        raise _erro()
    attrs = no.get("attrs") or {}
    if not isinstance(attrs, dict):
        raise _erro()
    if tipo == "heading" and attrs.get("level") not in (1, 2, 3):
        raise _erro()
    if tipo == "image":
        try:
            anexo = uuid.UUID(str(attrs.get("anexoId")))
        except ValueError as erro:
            raise _erro() from erro
        if anexos is not None and anexo not in anexos:
            raise ErroDeRegra("A imagem precisa ser um anexo deste item.")
        no["attrs"] = {"anexoId": str(anexo), "alt": str(attrs.get("alt") or "")[:200]}
    if tipo == "mention":
        try:
            uuid.UUID(str(attrs.get("id")))
        except ValueError as erro:
            raise _erro() from erro
        no["attrs"] = {"id": str(attrs["id"]), "label": str(attrs.get("label") or "")[:200]}
    for marca in no.get("marks") or []:
        if not isinstance(marca, dict) or marca.get("type") not in MARCAS_PERMITIDAS:
            raise _erro()
        if marca["type"] == "link":
            href = str((marca.get("attrs") or {}).get("href") or "")
            if not _ESQUEMAS_LINK.match(href):
                raise ErroDeRegra("Links precisam começar com http://, https:// ou mailto:.")
            marca["attrs"] = {"href": href[:2000]}
    filhos = no.get("content")
    if filhos is not None:
        if not isinstance(filhos, list):
            raise _erro()
        for filho in filhos:
            _conferir(filho, profundidade + 1, anexos)


def validar(documento: Any, anexos_do_item: set[uuid.UUID] | None = None) -> dict[str, Any] | None:
    """Confere o documento e devolve uma versão limpa. Documento vazio vira None."""
    if documento is None:
        return None
    if not isinstance(documento, dict) or documento.get("type") != "doc":
        raise _erro()
    if len(json.dumps(documento, ensure_ascii=False)) > TAMANHO_MAXIMO:
        raise ErroDeRegra("O texto está grande demais.")
    _conferir(documento, 0, anexos_do_item)
    return None if not texto_simples(documento).strip() and not _tem_imagem(documento) else documento


def _tem_imagem(no: dict[str, Any]) -> bool:
    if no.get("type") == "image":
        return True
    return any(_tem_imagem(f) for f in no.get("content") or [])


def texto_simples(no: dict[str, Any] | None) -> str:
    """Texto sem formatação (para histórico e busca)."""
    if not no:
        return ""
    if no.get("type") == "text":
        return no.get("text", "")
    if no.get("type") == "mention":
        return "@" + (no.get("attrs") or {}).get("label", "")
    partes = [texto_simples(f) for f in no.get("content") or []]
    separador = "\n" if no.get("type") in {"doc", "bulletList", "orderedList", "table", "tableRow"} else ""
    return separador.join(partes)


def mencoes(no: dict[str, Any] | None) -> set[str]:
    """Ids das pessoas mencionadas com @ (usados pelas notificações, na Etapa 8)."""
    if not no:
        return set()
    achados = {(no.get("attrs") or {}).get("id")} if no.get("type") == "mention" else set()
    for filho in no.get("content") or []:
        achados |= mencoes(filho)
    return {a for a in achados if a}


def anexos_citados(no: dict[str, Any] | None) -> set[str]:
    if not no:
        return set()
    achados = {(no.get("attrs") or {}).get("anexoId")} if no.get("type") == "image" else set()
    for filho in no.get("content") or []:
        achados |= anexos_citados(filho)
    return {a for a in achados if a}


def trocar_imagens(no: dict[str, Any] | None, mapa: dict[str, str]) -> dict[str, Any] | None:
    """Copia o documento trocando o anexo de cada imagem pelo novo id. Imagens sem par no mapa saem."""
    if not no:
        return None

    def copiar(atual: dict[str, Any]) -> dict[str, Any] | None:
        if atual.get("type") == "image":
            novo = mapa.get((atual.get("attrs") or {}).get("anexoId"))
            return {**atual, "attrs": {**atual["attrs"], "anexoId": novo}} if novo else None
        resultado = dict(atual)
        if "content" in atual:
            resultado["content"] = [c for c in (copiar(f) for f in atual.get("content") or []) if c is not None]
        return resultado

    documento = copiar(no)
    if documento is None or (not texto_simples(documento).strip() and not _tem_imagem(documento)):
        return None
    return documento
