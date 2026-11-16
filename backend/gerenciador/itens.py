"""Itens: criação, edição com histórico, exclusão e busca pela chave.

Campos padronizados (docs/decisoes-de-desenho.md):
- Obrigatórios: Resumo, Tipo, Espaço, Relator (automático), Status, Responsável, Prioridade, Time,
  Data de início e Data de entrega. Painel também, nos espaços que têm painéis.
- Opcionais: Descrição, Data real da entrega, Co-responsáveis, Categorias, Pai, Itens relacionados,
  Anexos, Origem da solicitação, Estimativa e Justificativa do atraso.
- Justificativa do atraso passa a ser obrigatória quando a entrega real passa da data de entrega.
"""

import re
import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from . import campos as campos_svc
from . import relogio, texto_rico
from .auditoria import TipoEvento, registrar
from .erros import ErroDeRegra, NaoEncontrado, OperacaoNegada, SemPermissao
from .espacos import listar_paineis, listar_status, listar_tipos, pode_no_espaco
from .modelos import Usuario
from .modelos_espacos import Espaco, OpcaoOrigem, Painel, StatusItem, TimeProvisorio, TipoItem
from .modelos_itens import PRIORIDADES, Anexo, ApelidoItem, CoResponsavel, HistoricoItem, Item

_CHAVE = re.compile(r"^([A-Za-z]{2,10})-(\d{1,9})$")

# Campos que a pessoa pode mandar ao criar ou editar.
CAMPOS_PADRAO = {
    "tipo_id", "resumo", "descricao", "status_id", "prioridade", "responsavel_id", "time_id",
    "data_inicio", "data_entrega", "data_real_entrega", "justificativa_atraso", "estimativa", "estimativa_horas",
    "pai_id", "painel_id", "origem_id", "categorias", "co_responsaveis", "valores",
}

ROTULOS = {
    "tipo_id": "Tipo", "resumo": "Resumo", "descricao": "Descrição", "status_id": "Status",
    "prioridade": "Prioridade", "responsavel_id": "Responsável", "time_id": "Time",
    "data_inicio": "Data de início", "data_entrega": "Data de entrega", "data_real_entrega": "Data real da entrega",
    "justificativa_atraso": "Justificativa do atraso", "estimativa": "Estimativa", "estimativa_horas": "Estimativa em horas",
    "pai_id": "Pai",
    "painel_id": "Painel", "origem_id": "Origem da solicitação", "categorias": "Categorias",
    "co_responsaveis": "Co-responsáveis",
}


def chave(espaco: Espaco, item: Item) -> str:
    return f"{espaco.sigla}-{item.numero}"


# --- Busca ------------------------------------------------------------------------------------

def localizar(db: Session, texto_chave: str) -> tuple[Item, Espaco] | None:
    """Acha o item pela chave atual ou por uma chave antiga (apelido). Não confere permissão."""
    texto_chave = texto_chave.strip().upper()
    casamento = _CHAVE.match(texto_chave)
    if not casamento:
        return None
    sigla, numero = casamento.group(1), int(casamento.group(2))
    par = db.execute(
        select(Item, Espaco).join(Espaco, Espaco.id == Item.espaco_id)
        .where(Espaco.sigla == sigla, Item.numero == numero, Item.excluido_em.is_(None))
    ).first()
    if par is None:
        apelido = db.get(ApelidoItem, texto_chave)
        if apelido is None:
            return None
        par = db.execute(
            select(Item, Espaco).join(Espaco, Espaco.id == Item.espaco_id)
            .where(Item.id == apelido.item_id, Item.excluido_em.is_(None))
        ).first()
    return (par[0], par[1]) if par else None


def buscar(db: Session, usuario: Usuario, texto_chave: str, acao: str = "ver") -> tuple[Item, Espaco]:
    achado = localizar(db, texto_chave)
    if achado is None or not pode_no_espaco(db, usuario, achado[1], "ver"):
        raise NaoEncontrado("Item não encontrado.")
    if acao != "ver" and not pode_no_espaco(db, usuario, achado[1], acao):
        raise SemPermissao("Você não tem permissão para esta ação.")
    return achado


@dataclass
class Filtros:
    busca: str | None = None
    tipo_id: uuid.UUID | None = None
    status_id: uuid.UUID | None = None
    painel_id: uuid.UUID | None = None
    responsavel_id: uuid.UUID | None = None


def listar(db: Session, espaco: Espaco, filtros: Filtros) -> list[Item]:
    consulta = select(Item).where(Item.espaco_id == espaco.id, Item.excluido_em.is_(None))
    if filtros.busca and filtros.busca.strip():
        termo = filtros.busca.strip()
        casamento = re.match(r"^\d+$", termo)
        condicoes = [Item.resumo.ilike(f"%{termo}%")]
        if casamento:
            condicoes.append(Item.numero == int(termo))
        consulta = consulta.where(or_(*condicoes))
    for campo in ("tipo_id", "status_id", "painel_id", "responsavel_id"):
        valor = getattr(filtros, campo)
        if valor:
            consulta = consulta.where(getattr(Item, campo) == valor)
    return list(db.scalars(consulta.order_by(Item.numero.desc()).limit(500)))


def filhos(db: Session, item: Item) -> list[Item]:
    return list(db.scalars(select(Item).where(Item.pai_id == item.id, Item.excluido_em.is_(None)).order_by(Item.numero)))


def co_responsaveis(db: Session, item: Item) -> list[uuid.UUID]:
    return list(db.scalars(select(CoResponsavel.usuario_id).where(CoResponsavel.item_id == item.id)))


def categorias_do_espaco(db: Session, espaco: Espaco) -> list[str]:
    """Etiquetas já usadas no espaço, para sugestão (decisão de 16/11)."""
    linhas = db.scalars(
        select(func.unnest(Item.categorias)).where(Item.espaco_id == espaco.id, Item.excluido_em.is_(None)).distinct()
    )
    return sorted(set(linhas), key=str.lower)


# --- Conferência dos campos -------------------------------------------------------------------

def _pode_ser_responsavel(db: Session, espaco: Espaco) -> set[uuid.UUID]:
    """Responsável e co-responsáveis precisam poder editar itens: ADM ou Membro (direto ou por time), ou o dono no pessoal."""
    from .espacos import pessoas_com_papel

    if espaco.tipo == "pessoal":
        return {espaco.dono_id} if espaco.dono_id else set()
    return pessoas_com_papel(db, espaco, {"adm", "membro"})


def _uuid(valor: Any, rotulo: str) -> uuid.UUID | None:
    if valor in (None, ""):
        return None
    try:
        return uuid.UUID(str(valor))
    except ValueError as erro:
        raise ErroDeRegra(f"{rotulo}: valor inválido.") from erro


def _data(valor: Any, rotulo: str) -> date | None:
    if valor in (None, ""):
        return None
    if isinstance(valor, date):
        return valor
    try:
        return date.fromisoformat(str(valor))
    except ValueError as erro:
        raise ErroDeRegra(f"{rotulo}: data inválida.") from erro


def _categorias(valor: Any) -> list[str]:
    if valor in (None, ""):
        return []
    if not isinstance(valor, list):
        raise ErroDeRegra("Categorias: valor inválido.")
    vistas, resultado = set(), []
    for bruta in valor:
        etiqueta = str(bruta).strip()
        if not etiqueta:
            continue
        if len(etiqueta) > 60:
            raise ErroDeRegra("Categorias: cada etiqueta pode ter até 60 caracteres.")
        if etiqueta.lower() not in vistas:
            vistas.add(etiqueta.lower())
            resultado.append(etiqueta)
    if len(resultado) > 20:
        raise ErroDeRegra("Categorias: até 20 etiquetas por item.")
    return resultado


@dataclass
class Estado:
    """Os valores de um item já conferidos, prontos para gravar."""

    tipo: TipoItem
    resumo: str
    descricao: dict | None
    status_id: uuid.UUID
    prioridade: str
    responsavel_id: uuid.UUID
    time_id: uuid.UUID
    data_inicio: date
    data_entrega: date
    data_real_entrega: date | None
    justificativa_atraso: str | None
    estimativa: Decimal | None
    estimativa_horas: Decimal | None
    pai_id: uuid.UUID | None
    painel_id: uuid.UUID | None
    origem_id: uuid.UUID | None
    categorias: list[str]
    co_responsaveis: list[uuid.UUID]
    valores: dict[str, Any]


def _conferir(
    db: Session, espaco: Espaco, dados: dict[str, Any], atual: Item | None, anexos: set[uuid.UUID] | None
) -> Estado:
    """Confere o estado final do item (o que já existe + o que mudou). Mensagens em português, campo a campo."""
    desconhecidos = set(dados) - CAMPOS_PADRAO
    if desconhecidos:
        raise ErroDeRegra("Campo desconhecido: " + ", ".join(sorted(desconhecidos)))

    def valor(campo: str) -> Any:
        if campo in dados:
            return dados[campo]
        if atual is None:
            return None
        if campo == "co_responsaveis":
            return co_responsaveis(db, atual)
        return getattr(atual, campo)

    tipos = {t.id: t for t in listar_tipos(db, espaco)}
    tipo_id = _uuid(valor("tipo_id"), "Tipo")
    if tipo_id is None:
        raise ErroDeRegra("Informe o tipo.")
    if tipo_id not in tipos:
        raise ErroDeRegra("Tipo inválido.")
    tipo = tipos[tipo_id]

    resumo = str(valor("resumo") or "").strip()
    if not resumo:
        raise ErroDeRegra("Informe o resumo.")
    if len(resumo) > 255:
        raise ErroDeRegra("O resumo pode ter até 255 caracteres.")

    descricao = texto_rico.validar(dados["descricao"], anexos) if "descricao" in dados else (
        atual.descricao if atual else None
    )

    status_id = _uuid(valor("status_id"), "Status")
    if status_id is None:
        raise ErroDeRegra("Informe o status.")
    if status_id not in {s.id for s in listar_status(db, espaco)}:
        raise ErroDeRegra("Status inválido.")

    prioridade = valor("prioridade")
    if not prioridade:
        raise ErroDeRegra("Informe a prioridade.")
    if prioridade not in PRIORIDADES:
        raise ErroDeRegra("Prioridade inválida.")

    responsaveis_possiveis = _pode_ser_responsavel(db, espaco)
    responsavel_id = _uuid(valor("responsavel_id"), "Responsável")
    if responsavel_id is None:
        raise ErroDeRegra("Informe o responsável.")
    if responsavel_id not in responsaveis_possiveis and (atual is None or "responsavel_id" in dados):
        raise ErroDeRegra("O responsável precisa ser ADM ou Membro do espaço.")

    time_id = _uuid(valor("time_id"), "Time")
    if time_id is None:
        raise ErroDeRegra("Informe o time.")
    time = db.get(TimeProvisorio, time_id)
    if time is None or (not time.ativo and (atual is None or atual.time_id != time_id)):
        raise ErroDeRegra("Time inválido.")

    data_inicio = _data(valor("data_inicio"), "Data de início")
    data_entrega = _data(valor("data_entrega"), "Data de entrega")
    if data_inicio is None:
        raise ErroDeRegra("Informe a data de início.")
    if data_entrega is None:
        raise ErroDeRegra("Informe a data de entrega.")
    if data_entrega < data_inicio:
        raise ErroDeRegra("A data de entrega não pode ser antes da data de início.")
    data_real = _data(valor("data_real_entrega"), "Data real da entrega")
    justificativa = (str(valor("justificativa_atraso") or "").strip() or None)
    if data_real and data_real > data_entrega and not justificativa:
        raise ErroDeRegra("A entrega real passou da data de entrega: informe a justificativa do atraso.")

    def numero(campo: str, rotulo: str) -> Decimal | None:
        bruto = valor(campo)
        if bruto in (None, ""):
            return None
        try:
            convertido = Decimal(str(bruto))
        except InvalidOperation as erro:
            raise ErroDeRegra(f"{rotulo}: valor inválido.") from erro
        if not convertido.is_finite() or convertido < 0 or convertido >= Decimal("1000000"):
            raise ErroDeRegra(f"{rotulo}: valor inválido.")
        return convertido

    estimativa = numero("estimativa", "Estimativa")
    estimativa_horas = numero("estimativa_horas", "Estimativa em horas")

    pai_id = _uuid(valor("pai_id"), "Pai")
    if tipo.nivel == "epico" and pai_id:
        raise ErroDeRegra("Um Épico não pode ter pai.")
    if tipo.nivel == "subtarefa" and not pai_id:
        raise ErroDeRegra("Uma Subtarefa precisa de um item pai.")
    if pai_id:
        pai = db.get(Item, pai_id)
        if pai is None or pai.espaco_id != espaco.id or pai.excluido_em is not None:
            raise ErroDeRegra("O item pai precisa ser deste espaço.")
        if atual is not None and pai.id == atual.id:
            raise ErroDeRegra("Um item não pode ser pai dele mesmo.")
        nivel_pai = tipos[pai.tipo_id].nivel if pai.tipo_id in tipos else None
        esperado = {"padrao": "epico", "subtarefa": "padrao"}.get(tipo.nivel)
        if nivel_pai != esperado:
            raise ErroDeRegra(
                "O pai de uma História, Tarefa ou Bug precisa ser um Épico."
                if tipo.nivel == "padrao"
                else "O pai de uma Subtarefa precisa ser uma História, Tarefa, Bug ou tipo próprio."
            )
    if atual is not None and tipo.nivel != tipos.get(atual.tipo_id, tipo).nivel and filhos(db, atual):
        raise ErroDeRegra("Este item tem filhos: mova-os antes de mudar o tipo para outro nível.")

    paineis = {p.id for p in listar_paineis(db, espaco)}
    painel_id = _uuid(valor("painel_id"), "Painel")
    if paineis and painel_id is None:
        raise ErroDeRegra("Informe o painel.")
    if painel_id is not None and painel_id not in paineis:
        raise ErroDeRegra("Painel inválido.")

    origem_id = _uuid(valor("origem_id"), "Origem da solicitação")
    if origem_id is not None:
        origem = db.get(OpcaoOrigem, origem_id)
        if origem is None or origem.espaco_id != espaco.id:
            raise ErroDeRegra("Origem da solicitação inválida.")
        if not origem.ativo and (atual is None or atual.origem_id != origem_id):
            raise ErroDeRegra("Essa origem não está mais disponível.")

    co_ids_brutos = valor("co_responsaveis") or []
    if not isinstance(co_ids_brutos, list):
        raise ErroDeRegra("Co-responsáveis: valor inválido.")
    co_ids = [u for u in (_uuid(i, "Co-responsáveis") for i in dict.fromkeys(co_ids_brutos)) if u]
    if "co_responsaveis" in dados and any(u not in responsaveis_possiveis for u in co_ids):
        raise ErroDeRegra("Os co-responsáveis precisam ser ADM ou Membro do espaço.")
    co_ids = [u for u in co_ids if u != responsavel_id]

    # Campos personalizados do tipo.
    valores_atuais = dict(atual.valores) if atual else {}
    novos = dados.get("valores") or {}
    if not isinstance(novos, dict):
        raise ErroDeRegra("Valores dos campos personalizados inválidos.")
    campos = {str(c.id): c for c in campos_svc.campos_do_tipo(db, espaco, tipo.id)}
    for cid in novos:
        if cid not in campos:
            raise ErroDeRegra("Campo personalizado inválido para este tipo.")
    valores = {}
    for cid, campo in campos.items():
        if cid in novos:
            valores[cid] = campos_svc.normalizar_valor(db, espaco, campo, novos[cid], valores_atuais.get(cid))
        else:
            valores[cid] = valores_atuais.get(cid)
        exigir_agora = atual is None or cid in novos
        if campo.obrigatorio and exigir_agora and valores[cid] is None:
            raise ErroDeRegra(f"Informe {campo.nome}.")
    # Valores de campos que não valem para o tipo continuam guardados (podem voltar se o tipo mudar).
    for cid, v in valores_atuais.items():
        valores.setdefault(cid, v)
    valores = {k: v for k, v in valores.items() if v is not None}

    return Estado(
        tipo=tipo, resumo=resumo, descricao=descricao, status_id=status_id, prioridade=prioridade,
        responsavel_id=responsavel_id, time_id=time_id, data_inicio=data_inicio, data_entrega=data_entrega,
        data_real_entrega=data_real, justificativa_atraso=justificativa, estimativa=estimativa,
        estimativa_horas=estimativa_horas, pai_id=pai_id,
        painel_id=painel_id, origem_id=origem_id, categorias=_categorias(valor("categorias")),
        co_responsaveis=co_ids, valores=valores,
    )


# --- Texto legível para o histórico ----------------------------------------------------------

def _nome_de(db: Session, modelo, valor: Any) -> str | None:
    if valor is None:
        return None
    objeto = db.get(modelo, valor)
    return getattr(objeto, "nome", None) if objeto else "?"


def _texto(db: Session, espaco: Espaco, campo: str, valor: Any) -> str | None:
    if valor is None or valor == [] or valor == "":
        return None
    if campo == "tipo_id":
        return _nome_de(db, TipoItem, valor)
    if campo == "status_id":
        return _nome_de(db, StatusItem, valor)
    if campo == "time_id":
        return _nome_de(db, TimeProvisorio, valor)
    if campo == "painel_id":
        return _nome_de(db, Painel, valor)
    if campo == "origem_id":
        return _nome_de(db, OpcaoOrigem, valor)
    if campo == "responsavel_id":
        return _nome_de(db, Usuario, valor)
    if campo == "co_responsaveis":
        return ", ".join(filter(None, (_nome_de(db, Usuario, u) for u in valor)))
    if campo == "prioridade":
        return PRIORIDADES.get(valor, valor)
    if campo == "pai_id":
        pai = db.get(Item, valor)
        return chave(espaco, pai) + " " + pai.resumo if pai else "?"
    if campo == "categorias":
        return ", ".join(valor)
    if campo == "descricao":
        texto = texto_rico.texto_simples(valor).strip()
        return (texto[:300] + "…") if len(texto) > 300 else texto
    if isinstance(valor, date):
        return valor.strftime("%d/%m/%Y")
    if isinstance(valor, Decimal):
        return format(valor.normalize(), "f")
    return str(valor)


def _historico(db: Session, item: Item, autor: Usuario, campo: str, antes: str | None, depois: str | None) -> None:
    db.add(HistoricoItem(item_id=item.id, autor_id=autor.id, ocorrido_em=relogio.agora(), campo=campo,
                         valor_anterior=antes, valor_novo=depois))


# --- Criar, editar e excluir -----------------------------------------------------------------

def registrar_mudanca_status(
    db: Session, item: Item, de: StatusItem | None, para: StatusItem, quando=None
) -> None:
    """Guarda cada mudança de status com a categoria de destino (base do fluxo acumulado e do tempo de ciclo)."""
    from .modelos_scrum import MudancaStatus

    db.add(MudancaStatus(item_id=item.id, de_status_id=de.id if de else None, para_status_id=para.id,
                         categoria=para.categoria, quando=quando or relogio.agora()))


def criar(db: Session, ator: Usuario, espaco: Espaco, dados: dict[str, Any]) -> Item:
    if not pode_no_espaco(db, ator, espaco, "criar_itens"):
        raise SemPermissao("Você não tem permissão para criar itens neste espaço.")
    if dados.get("descricao") and texto_rico.anexos_citados(dados["descricao"]):
        raise ErroDeRegra("Adicione imagens à descrição depois de criar o item.")
    estado = _conferir(db, espaco, dados, None, set())
    # Trava o espaço para dois itens criados ao mesmo tempo não receberem o mesmo número.
    espaco = db.scalar(select(Espaco).where(Espaco.id == espaco.id).with_for_update())
    agora = relogio.agora()
    item = Item(
        espaco_id=espaco.id, numero=espaco.proximo_numero, tipo_id=estado.tipo.id, resumo=estado.resumo,
        descricao=estado.descricao, status_id=estado.status_id, prioridade=estado.prioridade,
        responsavel_id=estado.responsavel_id, relator_id=ator.id, time_id=estado.time_id,
        data_inicio=estado.data_inicio, data_entrega=estado.data_entrega,
        data_real_entrega=estado.data_real_entrega, justificativa_atraso=estado.justificativa_atraso,
        estimativa=estado.estimativa, estimativa_horas=estado.estimativa_horas, pai_id=estado.pai_id, painel_id=estado.painel_id,
        origem_id=estado.origem_id, categorias=estado.categorias, valores=estado.valores,
        criado_em=agora, atualizado_em=agora,
    )
    espaco.proximo_numero += 1
    db.add(item)
    db.flush()
    for uid in estado.co_responsaveis:
        db.add(CoResponsavel(item_id=item.id, usuario_id=uid))
    registrar_mudanca_status(db, item, None, db.get(StatusItem, item.status_id), agora)
    db.add(HistoricoItem(item_id=item.id, autor_id=ator.id, ocorrido_em=agora, campo="criado",
                         valor_anterior=None, valor_novo=chave(espaco, item)))
    db.commit()
    return item


class AvisoConcluirBloqueado(OperacaoNegada):
    """Concluir item ainda bloqueado é permitido, com alerta e confirmação (docs/decisoes-de-desenho.md)."""

    def __init__(self, bloqueios: list[str]):
        super().__init__("Este item ainda é bloqueado por: " + ", ".join(bloqueios) + ". Concluir mesmo assim?")
        self.bloqueios = bloqueios


def editar(
    db: Session, ator: Usuario, item: Item, espaco: Espaco, dados: dict[str, Any], *,
    confirmar_bloqueio: bool = False, ip: str | None = None,
) -> Item:
    from .vinculos import bloqueios_abertos

    if not pode_no_espaco(db, ator, espaco, "editar_itens"):
        raise SemPermissao("Você não tem permissão para editar itens neste espaço.")
    anexos = set(db.scalars(select(Anexo.id).where(Anexo.item_id == item.id, Anexo.excluido_em.is_(None))))
    estado = _conferir(db, espaco, dados, item, anexos)
    novo_status = db.get(StatusItem, estado.status_id)
    status_atual = db.get(StatusItem, item.status_id)
    from .workflow import conferir_transicao

    conferir_transicao(db, espaco, status_atual, novo_status)
    if novo_status.id != status_atual.id:
        registrar_mudanca_status(db, item, status_atual, novo_status)
    if novo_status.categoria == "concluido" and status_atual.categoria != "concluido":
        bloqueios = bloqueios_abertos(db, ator, item)
        if bloqueios and not confirmar_bloqueio:
            raise AvisoConcluirBloqueado(bloqueios)
        if bloqueios:
            _historico(db, item, ator, "Conclusão com bloqueio aberto", None,
                       f"Confirmada por {ator.nome}. Ainda bloqueado por: {', '.join(bloqueios)}")
            registrar(db, TipoEvento.CONCLUSAO_COM_BLOQUEIO, ator_id=ator.id, ip=ip, item=chave(espaco, item),
                      bloqueios=bloqueios)
    co_antes = co_responsaveis(db, item)
    mudou = False
    for campo in ROTULOS:
        if campo == "co_responsaveis":
            antes, depois = co_antes, estado.co_responsaveis
            if set(antes) != set(depois):
                for uid in set(antes) - set(depois):
                    db.query(CoResponsavel).filter_by(item_id=item.id, usuario_id=uid).delete()
                for uid in set(depois) - set(antes):
                    db.add(CoResponsavel(item_id=item.id, usuario_id=uid))
                _historico(db, item, ator, ROTULOS[campo], _texto(db, espaco, campo, antes),
                           _texto(db, espaco, campo, depois))
                mudou = True
            continue
        antes = getattr(item, campo)
        depois = estado.tipo.id if campo == "tipo_id" else getattr(estado, campo)
        if antes != depois:
            setattr(item, campo, depois)
            _historico(db, item, ator, ROTULOS[campo], _texto(db, espaco, campo, antes),
                       _texto(db, espaco, campo, depois))
            mudou = True
    if item.valores != estado.valores:
        campos = {str(c.id): c for c in campos_svc.listar(db, espaco, incluir_inativos=True)}
        for cid in set(item.valores) | set(estado.valores):
            antes, depois = item.valores.get(cid), estado.valores.get(cid)
            if antes != depois and cid in campos:
                c = campos[cid]
                _historico(db, item, ator, c.nome, campos_svc.texto_do_valor(db, c, antes),
                           campos_svc.texto_do_valor(db, c, depois))
        item.valores = estado.valores
        mudou = True
    if mudou:
        item.atualizado_em = relogio.agora()
    db.commit()
    return item


def excluir(db: Session, ator: Usuario, item: Item, espaco: Espaco, ip: str | None) -> None:
    """ADM do espaço exclui qualquer item; Membro exclui os próprios (os que ele criou)."""
    pode = pode_no_espaco(db, ator, espaco, "excluir_qualquer_item") or (
        item.relator_id == ator.id and pode_no_espaco(db, ator, espaco, "excluir_proprios_itens")
    )
    if not pode:
        raise SemPermissao("Você não tem permissão para excluir este item.")
    if filhos(db, item):
        raise OperacaoNegada("Este item tem itens filhos. Exclua ou mova os filhos antes.")
    item.excluido_em = relogio.agora()
    item.excluido_por_id = ator.id
    registrar(db, TipoEvento.ITEM_EXCLUIDO, ator_id=ator.id, ip=ip, item=chave(espaco, item), resumo=item.resumo)
    db.commit()


def clonar(
    db: Session, ator: Usuario, item: Item, espaco: Espaco, *, copiar_comentarios: bool = False,
    copiar_anexos: bool = False,
) -> Item:
    """Cria uma cópia com os mesmos campos e o vínculo "Clona" (docs/decisoes-de-desenho.md).
    Antes, a pessoa escolhe se copia também os comentários e os anexos (com as imagens da descrição).
    O histórico nunca é copiado."""
    from .armazenamento import obter_armazenamento
    from .modelos_itens import Comentario
    from .vinculos import criar_vinculo_sistema

    dados = {
        "tipo_id": item.tipo_id, "resumo": item.resumo, "status_id": item.status_id,
        "prioridade": item.prioridade, "responsavel_id": item.responsavel_id, "time_id": item.time_id,
        "data_inicio": item.data_inicio, "data_entrega": item.data_entrega,
        "data_real_entrega": item.data_real_entrega, "justificativa_atraso": item.justificativa_atraso,
        "estimativa": item.estimativa, "estimativa_horas": item.estimativa_horas, "pai_id": item.pai_id,
        "painel_id": item.painel_id,
        "origem_id": item.origem_id, "categorias": list(item.categorias),
        "co_responsaveis": co_responsaveis(db, item),
        "valores": {cid: v for cid, v in item.valores.items()
                    if cid in {str(c.id) for c in campos_svc.campos_do_tipo(db, espaco, item.tipo_id)}},
    }
    copia = criar(db, ator, espaco, dados)

    # Anexos: cada arquivo é copiado, para a cópia não depender do original.
    mapa: dict[str, str] = {}
    if copiar_anexos:
        armazenamento = obter_armazenamento()
        for anexo in db.scalars(select(Anexo).where(Anexo.item_id == item.id, Anexo.excluido_em.is_(None))):
            novo = Anexo(item_id=copia.id, nome_arquivo=anexo.nome_arquivo, tipo_mime=anexo.tipo_mime,
                         tamanho=anexo.tamanho, chave_armazenamento=armazenamento.copiar(anexo.chave_armazenamento),
                         enviado_por_id=anexo.enviado_por_id, enviado_em=anexo.enviado_em)
            db.add(novo)
            db.flush()
            mapa[str(anexo.id)] = str(novo.id)
    # Imagens apontam para os anexos copiados; sem copiar anexos, as imagens saem e o texto fica.
    copia.descricao = texto_rico.trocar_imagens(item.descricao, mapa)

    if copiar_comentarios:
        for c in db.scalars(select(Comentario).where(Comentario.item_id == item.id, Comentario.excluido_em.is_(None))
                            .order_by(Comentario.criado_em)):
            corpo = texto_rico.trocar_imagens(c.corpo, mapa)
            if corpo:
                db.add(Comentario(item_id=copia.id, autor_id=c.autor_id, corpo=corpo, criado_em=c.criado_em,
                                  editado_em=c.editado_em))

    copiado = [nome for nome, sim in (("comentários", copiar_comentarios), ("anexos", copiar_anexos)) if sim]
    db.add(HistoricoItem(item_id=copia.id, autor_id=ator.id, ocorrido_em=relogio.agora(), campo="Clonado de",
                         valor_anterior=None,
                         valor_novo=chave(espaco, item) + (f" (com {' e '.join(copiado)})" if copiado else "")))
    criar_vinculo_sistema(db, ator, "clona", copia, item)
    db.commit()
    return copia
