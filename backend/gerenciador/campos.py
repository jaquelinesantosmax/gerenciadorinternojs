"""Campos personalizados: criados pelo ADM do espaço, com os tipos decididos em 16/11.

Ao criar um campo, o ADM escolhe em quais tipos de item ele aparece e se é obrigatório.
"""

import re
import uuid
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import relogio
from .erros import ErroDeRegra, NaoEncontrado, OperacaoNegada, SemPermissao
from .espacos import listar_tipos, pode_no_espaco
from .modelos import Usuario
from .modelos_espacos import Espaco
from .modelos_itens import TIPOS_CAMPO, CampoPersonalizado

MOEDAS = {"BRL": "Real", "USD": "Dólar", "EUR": "Euro", "GBP": "Libra"}
_URL = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
TIPOS_LISTA = {"lista_unica", "lista_multipla", "lista_cascata"}


def _exigir_configurar(db: Session, ator: Usuario, espaco: Espaco) -> None:
    if not pode_no_espaco(db, ator, espaco, "configurar"):
        raise SemPermissao("Você não tem permissão para esta ação.")


def listar(db: Session, espaco: Espaco, incluir_inativos: bool = False) -> list[CampoPersonalizado]:
    consulta = (
        select(CampoPersonalizado)
        .where(CampoPersonalizado.espaco_id == espaco.id)
        .order_by(CampoPersonalizado.ordem, CampoPersonalizado.nome)
    )
    if not incluir_inativos:
        consulta = consulta.where(CampoPersonalizado.ativo)
    return list(db.scalars(consulta))


def _opcoes(cruas: Any, cascata: bool, anteriores: list[dict] | None = None) -> list[dict[str, Any]]:
    """Normaliza opções: [{id, nome, ativo, filhos?}]. Opções antigas mantêm o id (os itens guardam o id)."""
    if not isinstance(cruas, list):
        raise OperacaoNegada("Informe as opções da lista.")
    por_id = {o["id"]: o for o in anteriores or []}
    resultado, nomes = [], set()
    for crua in cruas:
        if not isinstance(crua, dict):
            raise OperacaoNegada("Opção inválida.")
        nome = str(crua.get("nome") or "").strip()
        if not nome:
            raise OperacaoNegada("Toda opção precisa de um nome.")
        if nome.lower() in nomes:
            raise OperacaoNegada(f"A opção {nome} está repetida.")
        nomes.add(nome.lower())
        oid = str(crua.get("id") or "")
        if oid not in por_id:
            oid = uuid.uuid4().hex
        opcao: dict[str, Any] = {"id": oid, "nome": nome[:120], "ativo": bool(crua.get("ativo", True))}
        if cascata:
            opcao["filhos"] = _opcoes(crua.get("filhos") or [], False, (por_id.get(oid) or {}).get("filhos"))
        resultado.append(opcao)
    # Opções que sumiram da lista continuam guardadas como inativas, para os itens que já as usam.
    for oid, antiga in por_id.items():
        if oid not in {o["id"] for o in resultado}:
            resultado.append({**antiga, "ativo": False})
    if not any(o["ativo"] for o in resultado):
        raise OperacaoNegada("A lista precisa de pelo menos uma opção ativa.")
    return resultado


def _config(tipo: str, crua: dict[str, Any], anterior: dict[str, Any] | None = None) -> dict[str, Any]:
    crua = crua or {}
    anterior = anterior or {}
    if tipo in TIPOS_LISTA:
        return {"opcoes": _opcoes(crua.get("opcoes"), tipo == "lista_cascata", anterior.get("opcoes"))}
    if tipo == "moeda":
        moeda = crua.get("moeda", anterior.get("moeda"))
        if moeda not in MOEDAS:
            raise OperacaoNegada("Escolha a moeda do campo.")
        return {"moeda": moeda}
    if tipo == "pessoa":
        return {"varias": bool(crua.get("varias", anterior.get("varias", False)))}
    if tipo == "sim_nao":
        # Texto livre que aparece ao lado da caixa de marcar (decisão de 16/11), ex.: "Envolve outra área?".
        texto = str(crua.get("texto", anterior.get("texto", "")) or "").strip()
        if len(texto) > 200:
            raise OperacaoNegada("O texto da caixa pode ter até 200 caracteres.")
        return {"texto": texto}
    return {}


def _tipos_item(db: Session, espaco: Espaco, ids: list[uuid.UUID]) -> list[uuid.UUID]:
    validos = {t.id for t in listar_tipos(db, espaco)}
    ids = list(dict.fromkeys(ids))
    if not ids:
        raise OperacaoNegada("Escolha em quais tipos de item o campo aparece.")
    if any(i not in validos for i in ids):
        raise OperacaoNegada("Tipo de item inválido.")
    return ids


def _nome(db: Session, espaco: Espaco, nome: str, ignorar: uuid.UUID | None = None) -> str:
    nome = nome.strip()
    if not nome:
        raise OperacaoNegada("Informe o nome do campo.")
    if len(nome) > 80:
        raise OperacaoNegada("O nome pode ter até 80 caracteres.")
    for campo in listar(db, espaco, incluir_inativos=True):
        if campo.nome.lower() == nome.lower() and campo.id != ignorar:
            raise OperacaoNegada(f"Já existe um campo chamado {campo.nome}.")
    return nome


def criar(
    db: Session, ator: Usuario, espaco: Espaco, nome: str, tipo: str, obrigatorio: bool,
    tipos_item: list[uuid.UUID], config: dict[str, Any],
) -> CampoPersonalizado:
    _exigir_configurar(db, ator, espaco)
    if tipo not in TIPOS_CAMPO:
        raise OperacaoNegada("Tipo de campo inválido.")
    campo = CampoPersonalizado(
        espaco_id=espaco.id,
        nome=_nome(db, espaco, nome),
        tipo=tipo,
        obrigatorio=obrigatorio,
        tipos_item=_tipos_item(db, espaco, tipos_item),
        config=_config(tipo, config),
        ordem=len(listar(db, espaco, incluir_inativos=True)),
        ativo=True,
        criado_em=relogio.agora(),
    )
    db.add(campo)
    db.commit()
    return campo


def buscar(db: Session, espaco: Espaco, campo_id: uuid.UUID) -> CampoPersonalizado:
    campo = db.get(CampoPersonalizado, campo_id)
    if campo is None or campo.espaco_id != espaco.id:
        raise NaoEncontrado("Campo não encontrado.")
    return campo


def editar(
    db: Session, ator: Usuario, espaco: Espaco, campo_id: uuid.UUID, *, nome: str | None = None,
    obrigatorio: bool | None = None, tipos_item: list[uuid.UUID] | None = None,
    config: dict[str, Any] | None = None, ativo: bool | None = None,
) -> CampoPersonalizado:
    """O tipo do campo não muda depois de criado, para não estragar os valores já preenchidos."""
    _exigir_configurar(db, ator, espaco)
    campo = buscar(db, espaco, campo_id)
    if nome is not None:
        campo.nome = _nome(db, espaco, nome, ignorar=campo.id)
    if obrigatorio is not None:
        campo.obrigatorio = obrigatorio
    if tipos_item is not None:
        campo.tipos_item = _tipos_item(db, espaco, tipos_item)
    if config is not None:
        campo.config = _config(campo.tipo, config, campo.config)
    if ativo is not None:
        campo.ativo = ativo
    db.commit()
    return campo


# --- Valores ----------------------------------------------------------------------------------

def _vazio(valor: Any) -> bool:
    return valor is None or valor == "" or valor == [] or valor == {}


def _opcao(opcoes: list[dict], oid: Any, nova: bool) -> dict:
    for opcao in opcoes:
        if opcao["id"] == oid:
            if nova and not opcao["ativo"]:
                raise ErroDeRegra("Essa opção não está mais disponível.")
            return opcao
    raise ErroDeRegra("Opção inválida.")


def normalizar_valor(
    db: Session, espaco: Espaco, campo: CampoPersonalizado, valor: Any, anterior: Any = None
) -> Any:
    """Confere o valor conforme o tipo do campo e devolve o formato guardado. Vazio vira None.
    Opções inativas são aceitas só se o item já tinha esse valor."""
    if _vazio(valor):
        return None
    nome = campo.nome
    t = campo.tipo
    try:
        if t in ("texto_curto", "texto_longo"):
            texto = str(valor).strip()
            limite = 255 if t == "texto_curto" else 10_000
            if len(texto) > limite:
                raise ErroDeRegra(f"{nome}: até {limite} caracteres.")
            return texto or None
        if t == "numero":
            if isinstance(valor, bool):
                raise ValueError
            numero = Decimal(str(valor))
            if not numero.is_finite():
                raise ValueError
            return float(numero) if numero != numero.to_integral_value() else int(numero)
        if t == "moeda":
            if isinstance(valor, bool):
                raise ValueError
            return str(Decimal(str(valor)).quantize(Decimal("0.01")))
        if t == "data":
            return date.fromisoformat(str(valor)).isoformat()
        if t == "data_hora":
            momento = datetime.fromisoformat(str(valor))
            if momento.tzinfo is None:
                raise ErroDeRegra(f"{nome}: informe o fuso horário.")
            return momento.isoformat()
        if t == "url":
            url = str(valor).strip()
            if not _URL.match(url) or len(url) > 2000:
                raise ErroDeRegra(f"{nome}: o endereço precisa começar com http:// ou https://.")
            return url
        if t == "sim_nao":
            if not isinstance(valor, bool):
                raise ValueError
            return valor
        opcoes = campo.config.get("opcoes", [])
        if t == "lista_unica":
            return _opcao(opcoes, valor, valor != anterior)["id"]
        if t == "lista_multipla":
            if not isinstance(valor, list):
                raise ValueError
            antigos = set(anterior or [])
            return [_opcao(opcoes, v, v not in antigos)["id"] for v in dict.fromkeys(valor)] or None
        if t == "lista_cascata":
            if not isinstance(valor, dict):
                raise ValueError
            antigo = anterior or {}
            pai = _opcao(opcoes, valor.get("pai"), valor.get("pai") != antigo.get("pai"))
            filho = valor.get("filho")
            if filho is None:
                return {"pai": pai["id"], "filho": None}
            filho_ok = _opcao(pai.get("filhos", []), filho, filho != antigo.get("filho"))
            return {"pai": pai["id"], "filho": filho_ok["id"]}
        if t == "pessoa":
            ids = valor if isinstance(valor, list) else [valor]
            if not campo.config.get("varias") and len(ids) > 1:
                raise ErroDeRegra(f"{nome}: escolha só uma pessoa.")
            ids = [str(uuid.UUID(str(i))) for i in dict.fromkeys(ids)]
            membros = _membros_do_espaco(db, espaco)
            if any(i not in membros for i in ids):
                raise ErroDeRegra(f"{nome}: escolha pessoas que são membros do espaço.")
            return ids if campo.config.get("varias") else ids[0]
    except ErroDeRegra:
        raise
    except (ValueError, TypeError, InvalidOperation) as erro:
        raise ErroDeRegra(f"{nome}: valor inválido.") from erro
    raise ErroDeRegra(f"{nome}: tipo de campo desconhecido.")


def _membros_do_espaco(db: Session, espaco: Espaco) -> set[str]:
    if espaco.tipo == "pessoal":
        return {str(espaco.dono_id)}
    from .espacos import pessoas_com_papel

    return {str(u) for u in pessoas_com_papel(db, espaco, {"adm", "membro", "leitor"})}


def campos_do_tipo(db: Session, espaco: Espaco, tipo_id: uuid.UUID) -> list[CampoPersonalizado]:
    return [c for c in listar(db, espaco) if tipo_id in c.tipos_item]


def texto_do_valor(db: Session, campo: CampoPersonalizado, valor: Any) -> str | None:
    """Valor legível, para o histórico."""
    if valor is None:
        return None
    opcoes = {o["id"]: o for o in campo.config.get("opcoes", [])}
    if campo.tipo == "lista_unica":
        return opcoes.get(valor, {}).get("nome", "?")
    if campo.tipo == "lista_multipla":
        return ", ".join(opcoes.get(v, {}).get("nome", "?") for v in valor)
    if campo.tipo == "lista_cascata":
        pai = opcoes.get(valor.get("pai"), {})
        filhos = {f["id"]: f for f in pai.get("filhos", [])}
        filho = filhos.get(valor.get("filho"), {}).get("nome")
        return pai.get("nome", "?") + (f" › {filho}" if filho else "")
    if campo.tipo == "pessoa":
        ids = valor if isinstance(valor, list) else [valor]
        nomes = [u.nome for u in (db.get(Usuario, uuid.UUID(i)) for i in ids) if u]
        return ", ".join(nomes)
    if campo.tipo == "sim_nao":
        return "Sim" if valor else "Não"
    if campo.tipo == "moeda":
        return f"{campo.config.get('moeda', '')} {valor}"
    return str(valor)
