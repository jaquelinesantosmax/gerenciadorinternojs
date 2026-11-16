"""Scrum e métricas (Etapa 3b).

- Backlog, sprints com início, fim e objetivo; estimativa por pontos, horas ou contagem de itens (por quadro).
- Um quadro pode ter várias sprints ativas ao mesmo tempo (decisão de 16/11).
- Um item fica em no máximo uma sprint aberta (planejada ou ativa) por vez.
- Ao entrar numa sprint, o item em Backlog passa para A fazer; voltar ao backlog não muda o status.
- Ao encerrar, quem encerra escolhe para onde vão os itens não concluídos: outra sprint, uma nova ou o backlog.
- Métricas: burndown, velocidade, relatório de sprint, fluxo acumulado e tempo de ciclo.
"""

import statistics
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import relogio
from .erros import ErroDeRegra, NaoEncontrado, OperacaoNegada, SemPermissao
from .espacos import pode_no_espaco
from .modelos import Usuario
from .modelos_espacos import Espaco, StatusItem
from .modelos_itens import HistoricoItem, Item
from .modelos_quadros import Quadro
from .modelos_scrum import UNIDADES_ESTIMATIVA, ItemDaSprint, MudancaStatus, Sprint
from .workflow import status_do_espaco

FUSO = timedelta(hours=-3)  # Brasília


def fim_do_dia(d: date) -> datetime:
    """Último instante do dia d no horário de Brasília, em UTC."""
    return datetime.combine(d + timedelta(days=1), time(0), tzinfo=UTC) - FUSO


def hoje_brasilia() -> date:
    return (relogio.agora() + FUSO).date()


def valor(item: Item, unidade: str) -> Decimal:
    if unidade == "itens":
        return Decimal(1)
    bruto = item.estimativa_horas if unidade == "horas" else item.estimativa
    return Decimal(bruto or 0)


def itens_do_quadro(db: Session, quadro: Quadro) -> list[Item]:
    consulta = select(Item).where(Item.espaco_id == quadro.espaco_id, Item.excluido_em.is_(None))
    if quadro.painel_id:
        consulta = consulta.where(Item.painel_id == quadro.painel_id)
    return list(db.scalars(consulta.order_by(Item.numero)))


def _categoria_atual(db: Session, item: Item) -> str:
    return db.get(StatusItem, item.status_id).categoria


# --- Permissões e busca -----------------------------------------------------------------------

def _exigir_sprints(db: Session, ator: Usuario, quadro: Quadro) -> Espaco:
    espaco = db.get(Espaco, quadro.espaco_id)
    if not pode_no_espaco(db, ator, espaco, "gerenciar_sprints"):
        raise SemPermissao("Você não tem permissão para gerenciar sprints neste espaço.")
    if quadro.tipo != "scrum":
        raise OperacaoNegada("Sprints só existem em quadros Scrum.")
    return espaco


def buscar_sprint(db: Session, sprint_id: uuid.UUID) -> tuple[Sprint, Quadro, Espaco]:
    sprint = db.get(Sprint, sprint_id)
    if sprint is None:
        raise NaoEncontrado("Sprint não encontrada.")
    quadro = db.get(Quadro, sprint.quadro_id)
    return sprint, quadro, db.get(Espaco, quadro.espaco_id)


def _ligacoes_abertas(db: Session, sprint: Sprint) -> list[ItemDaSprint]:
    return list(db.scalars(select(ItemDaSprint).where(ItemDaSprint.sprint_id == sprint.id,
                                                      ItemDaSprint.removido_em.is_(None))))


def itens_da_sprint(db: Session, sprint: Sprint) -> list[Item]:
    ids = [ligacao.item_id for ligacao in _ligacoes_abertas(db, sprint)]
    if not ids:
        return []
    return list(db.scalars(select(Item).where(Item.id.in_(ids), Item.excluido_em.is_(None)).order_by(Item.numero)))


def sprint_aberta_do_item(db: Session, item: Item) -> Sprint | None:
    return db.scalar(
        select(Sprint).join(ItemDaSprint, ItemDaSprint.sprint_id == Sprint.id)
        .where(ItemDaSprint.item_id == item.id, ItemDaSprint.removido_em.is_(None), Sprint.estado != "encerrada")
    )


def sprints_do_quadro(db: Session, quadro: Quadro) -> list[Sprint]:
    ordem = {"ativa": 0, "planejada": 1, "encerrada": 2}
    sprints = list(db.scalars(select(Sprint).where(Sprint.quadro_id == quadro.id).order_by(Sprint.criado_em)))
    return sorted(sprints, key=lambda s: (ordem[s.estado], -(s.encerrada_em.timestamp() if s.encerrada_em else 0)))


def backlog(db: Session, quadro: Quadro) -> list[Item]:
    """Itens do quadro ainda não concluídos que não estão em nenhuma sprint aberta."""
    em_sprint = set(db.scalars(
        select(ItemDaSprint.item_id).join(Sprint, Sprint.id == ItemDaSprint.sprint_id)
        .where(ItemDaSprint.removido_em.is_(None), Sprint.estado != "encerrada")
    ))
    return [i for i in itens_do_quadro(db, quadro) if i.id not in em_sprint and _categoria_atual(db, i) != "concluido"]


# --- Sprints ----------------------------------------------------------------------------------

def _datas(inicio: date | None, fim: date | None) -> None:
    if inicio and fim and fim < inicio:
        raise ErroDeRegra("O fim da sprint não pode ser antes do início.")


def criar_sprint(
    db: Session, ator: Usuario, quadro: Quadro, nome: str | None = None, objetivo: str | None = None,
    inicio: date | None = None, fim: date | None = None,
) -> Sprint:
    _exigir_sprints(db, ator, quadro)
    _datas(inicio, fim)
    quantas = db.scalar(select(func.count()).select_from(Sprint).where(Sprint.quadro_id == quadro.id)) or 0
    sprint = Sprint(quadro_id=quadro.id, nome=(nome or "").strip()[:120] or f"Sprint {quantas + 1}",
                    objetivo=(objetivo or "").strip() or None, inicio=inicio, fim=fim, estado="planejada",
                    criado_por_id=ator.id, criado_em=relogio.agora())
    db.add(sprint)
    db.commit()
    return sprint


def editar_sprint(
    db: Session, ator: Usuario, sprint: Sprint, quadro: Quadro, *, nome: str | None = None,
    objetivo: str | None = None, inicio: date | None = None, fim: date | None = None,
) -> None:
    _exigir_sprints(db, ator, quadro)
    if sprint.estado == "encerrada":
        raise OperacaoNegada("Sprint encerrada não muda mais.")
    if nome is not None:
        if not nome.strip():
            raise ErroDeRegra("Informe o nome da sprint.")
        sprint.nome = nome.strip()[:120]
    if objetivo is not None:
        sprint.objetivo = objetivo.strip() or None
    novo_inicio = inicio if inicio is not None else sprint.inicio
    novo_fim = fim if fim is not None else sprint.fim
    _datas(novo_inicio, novo_fim)
    sprint.inicio, sprint.fim = novo_inicio, novo_fim
    db.commit()


def excluir_sprint(db: Session, ator: Usuario, sprint: Sprint, quadro: Quadro) -> None:
    _exigir_sprints(db, ator, quadro)
    if sprint.estado != "planejada":
        raise OperacaoNegada("Só sprints que ainda não começaram podem ser excluídas.")
    db.delete(sprint)  # os itens voltam ao backlog
    db.commit()


def _sair_do_backlog(db: Session, ator: Usuario, item: Item, espaco: Espaco) -> None:
    """Decisão de 16/11: ao entrar numa sprint, o item em Backlog passa para A fazer."""
    from .itens import registrar_mudanca_status

    atual = db.get(StatusItem, item.status_id)
    if atual.nome != "Backlog" or atual.espaco_id is not None:
        return
    a_fazer = next((s for s in status_do_espaco(db, espaco) if s.nome == "A fazer" and s.espaco_id is None), None)
    if a_fazer is None:
        return
    item.status_id = a_fazer.id
    item.atualizado_em = relogio.agora()
    registrar_mudanca_status(db, item, atual, a_fazer)
    db.add(HistoricoItem(item_id=item.id, autor_id=ator.id, ocorrido_em=relogio.agora(), campo="Status",
                         valor_anterior=atual.nome, valor_novo=f"{a_fazer.nome} (entrou na sprint)"))


def adicionar_item(db: Session, ator: Usuario, sprint: Sprint, quadro: Quadro, item: Item) -> None:
    from .itens import chave

    espaco = _exigir_sprints(db, ator, quadro)
    if sprint.estado == "encerrada":
        raise OperacaoNegada("A sprint já foi encerrada.")
    if item.excluido_em is not None or item.id not in {i.id for i in itens_do_quadro(db, quadro)}:
        raise ErroDeRegra("O item precisa ser deste quadro.")
    outra = sprint_aberta_do_item(db, item)
    if outra is not None:
        if outra.id == sprint.id:
            raise OperacaoNegada(f"{chave(espaco, item)} já está nesta sprint.")
        raise OperacaoNegada(f"{chave(espaco, item)} já está na {outra.nome}. Tire de lá antes.")
    db.add(ItemDaSprint(sprint_id=sprint.id, item_id=item.id, adicionado_em=relogio.agora(),
                        adicionado_apos_inicio=sprint.estado == "ativa"))
    _sair_do_backlog(db, ator, item, espaco)
    db.add(HistoricoItem(item_id=item.id, autor_id=ator.id, ocorrido_em=relogio.agora(), campo="Sprint",
                         valor_anterior=None, valor_novo=sprint.nome))
    db.commit()


def remover_item(db: Session, ator: Usuario, sprint: Sprint, quadro: Quadro, item: Item) -> None:
    _exigir_sprints(db, ator, quadro)
    if sprint.estado == "encerrada":
        raise OperacaoNegada("A sprint já foi encerrada.")
    ligacao = db.scalar(select(ItemDaSprint).where(ItemDaSprint.sprint_id == sprint.id, ItemDaSprint.item_id == item.id,
                                                   ItemDaSprint.removido_em.is_(None)))
    if ligacao is None:
        raise NaoEncontrado("O item não está nesta sprint.")
    ligacao.removido_em = relogio.agora()
    db.add(HistoricoItem(item_id=item.id, autor_id=ator.id, ocorrido_em=relogio.agora(), campo="Sprint",
                         valor_anterior=sprint.nome, valor_novo=None))
    db.commit()


def total(db: Session, itens: list[Item], unidade: str, so_concluidos: bool = False) -> Decimal:
    return sum((valor(i, unidade) for i in itens if not so_concluidos or _categoria_atual(db, i) == "concluido"),
               Decimal(0))


def iniciar_sprint(db: Session, ator: Usuario, sprint: Sprint, quadro: Quadro,
                   inicio: date | None = None, fim: date | None = None) -> None:
    _exigir_sprints(db, ator, quadro)
    if sprint.estado != "planejada":
        raise OperacaoNegada("Essa sprint já começou.")
    sprint.inicio = inicio or sprint.inicio or hoje_brasilia()
    sprint.fim = fim or sprint.fim
    if sprint.fim is None:
        raise ErroDeRegra("Defina a data de fim da sprint.")
    _datas(sprint.inicio, sprint.fim)
    sprint.estado = "ativa"
    sprint.iniciada_em = relogio.agora()
    sprint.compromisso = total(db, itens_da_sprint(db, sprint), quadro.unidade_estimativa)
    db.commit()


def encerrar_sprint(db: Session, ator: Usuario, sprint: Sprint, quadro: Quadro, destino: str) -> Sprint | None:
    """destino: "backlog", "nova" ou o id de outra sprint aberta do mesmo quadro. Devolve a sprint de destino."""
    _exigir_sprints(db, ator, quadro)
    if sprint.estado != "ativa":
        raise OperacaoNegada("Só uma sprint ativa pode ser encerrada.")
    alvo: Sprint | None = None
    if destino == "nova":
        alvo = criar_sprint(db, ator, quadro)
    elif destino != "backlog":
        try:
            alvo = db.get(Sprint, uuid.UUID(destino))
        except ValueError as erro:
            raise ErroDeRegra("Destino inválido.") from erro
        if alvo is None or alvo.quadro_id != quadro.id or alvo.estado == "encerrada" or alvo.id == sprint.id:
            raise ErroDeRegra("Escolha uma sprint aberta deste quadro.")
    agora = relogio.agora()
    entregue = Decimal(0)
    for ligacao in _ligacoes_abertas(db, sprint):
        item = db.get(Item, ligacao.item_id)
        concluido = item.excluido_em is None and _categoria_atual(db, item) == "concluido"
        ligacao.concluido_na_sprint = concluido
        if concluido:
            entregue += valor(item, quadro.unidade_estimativa)
        elif alvo is not None and item.excluido_em is None:
            db.add(ItemDaSprint(sprint_id=alvo.id, item_id=item.id, adicionado_em=agora,
                                adicionado_apos_inicio=alvo.estado == "ativa"))
    sprint.estado = "encerrada"
    sprint.encerrada_em = agora
    sprint.entregue = entregue
    db.commit()
    return alvo


# --- Métricas ---------------------------------------------------------------------------------

def _categoria_em(db: Session, item_id: uuid.UUID, momento: datetime) -> str | None:
    return db.scalar(select(MudancaStatus.categoria).where(MudancaStatus.item_id == item_id, MudancaStatus.quando <= momento)
                     .order_by(MudancaStatus.quando.desc(), MudancaStatus.id.desc()).limit(1))


@dataclass
class PontoBurndown:
    dia: date
    restante: Decimal | None
    ideal: Decimal
    escopo: Decimal | None


def burndown(db: Session, sprint: Sprint, quadro: Quadro) -> list[PontoBurndown]:
    if sprint.inicio is None or sprint.fim is None or sprint.estado == "planejada":
        return []
    ligacoes = list(db.scalars(select(ItemDaSprint).where(ItemDaSprint.sprint_id == sprint.id)))
    itens = {i.id: i for i in db.scalars(select(Item).where(Item.id.in_([lg.item_id for lg in ligacoes])))} if ligacoes else {}
    ultimo_real = min(sprint.fim, (sprint.encerrada_em + FUSO).date() if sprint.encerrada_em else hoje_brasilia())
    dias = (sprint.fim - sprint.inicio).days
    compromisso = sprint.compromisso or Decimal(0)
    pontos = []
    for n in range(dias + 1):
        d = sprint.inicio + timedelta(days=n)
        ideal = (compromisso * (dias - n) / dias) if dias else Decimal(0)
        if d > ultimo_real:
            pontos.append(PontoBurndown(d, None, ideal.quantize(Decimal("0.01")), None))
            continue
        fim = fim_do_dia(d)
        escopo = restante = Decimal(0)
        for lg in ligacoes:
            if lg.adicionado_em > fim or (lg.removido_em is not None and lg.removido_em <= fim):
                continue
            item = itens[lg.item_id]
            v = valor(item, quadro.unidade_estimativa)
            escopo += v
            if _categoria_em(db, item.id, fim) != "concluido":
                restante += v
        pontos.append(PontoBurndown(d, restante, ideal.quantize(Decimal("0.01")), escopo))
    return pontos


@dataclass
class LinhaVelocidade:
    sprint: str
    compromisso: Decimal
    entregue: Decimal


def velocidade(db: Session, quadro: Quadro, quantas: int = 7) -> list[LinhaVelocidade]:
    encerradas = list(db.scalars(select(Sprint).where(Sprint.quadro_id == quadro.id, Sprint.estado == "encerrada")
                                 .order_by(Sprint.encerrada_em.desc()).limit(quantas)))
    return [LinhaVelocidade(s.nome, s.compromisso or Decimal(0), s.entregue or Decimal(0)) for s in reversed(encerradas)]


@dataclass
class Relatorio:
    concluidos: list[Item] = field(default_factory=list)
    nao_concluidos: list[Item] = field(default_factory=list)
    adicionados_depois: list[Item] = field(default_factory=list)
    removidos: list[Item] = field(default_factory=list)


def relatorio(db: Session, sprint: Sprint) -> Relatorio:
    r = Relatorio()
    for lg in db.scalars(select(ItemDaSprint).where(ItemDaSprint.sprint_id == sprint.id).order_by(ItemDaSprint.adicionado_em)):
        item = db.get(Item, lg.item_id)
        if item is None or item.excluido_em is not None:
            continue
        if lg.removido_em is not None:
            r.removidos.append(item)
            continue
        concluido = lg.concluido_na_sprint if sprint.estado == "encerrada" else _categoria_atual(db, item) == "concluido"
        (r.concluidos if concluido else r.nao_concluidos).append(item)
        if lg.adicionado_apos_inicio:
            r.adicionados_depois.append(item)
    return r


@dataclass
class DiaFluxo:
    dia: date
    a_fazer: int
    em_andamento: int
    concluido: int


def fluxo_acumulado(db: Session, quadro: Quadro, dias: int = 30) -> list[DiaFluxo]:
    hoje = hoje_brasilia()
    itens = itens_do_quadro(db, quadro)
    resultado = []
    for n in range(dias - 1, -1, -1):
        d = hoje - timedelta(days=n)
        contagem = {"a_fazer": 0, "em_andamento": 0, "concluido": 0}
        fim = fim_do_dia(d)
        for item in itens:
            categoria = _categoria_em(db, item.id, fim)
            if categoria in contagem:
                contagem[categoria] += 1
        resultado.append(DiaFluxo(d, **contagem))
    return resultado


@dataclass
class CicloItem:
    item: Item
    inicio: datetime
    fim: datetime
    dias: float


@dataclass
class TempoDeCiclo:
    itens: list[CicloItem]
    media: float | None
    mediana: float | None
    p85: float | None


def tempo_de_ciclo(db: Session, quadro: Quadro, dias: int = 90) -> TempoDeCiclo:
    """Do primeiro "Em andamento" até a conclusão, para itens concluídos no período."""
    desde = relogio.agora() - timedelta(days=dias)
    ciclos = []
    for item in itens_do_quadro(db, quadro):
        mudancas = list(db.scalars(select(MudancaStatus).where(MudancaStatus.item_id == item.id)
                                   .order_by(MudancaStatus.quando, MudancaStatus.id)))
        if not mudancas or mudancas[-1].categoria != "concluido" or mudancas[-1].quando < desde:
            continue
        fim = mudancas[-1].quando
        inicio = next((m.quando for m in mudancas if m.categoria == "em_andamento"), None)
        if inicio is None or inicio > fim:
            continue
        ciclos.append(CicloItem(item, inicio, fim, round((fim - inicio).total_seconds() / 86400, 1)))
    valores = sorted(c.dias for c in ciclos)
    if not valores:
        return TempoDeCiclo(ciclos, None, None, None)
    p85 = valores[min(len(valores) - 1, max(0, round(0.85 * len(valores) + 0.5) - 1))]
    return TempoDeCiclo(sorted(ciclos, key=lambda c: c.fim), round(statistics.fmean(valores), 1),
                        round(statistics.median(valores), 1), p85)


def definir_unidade(db: Session, ator: Usuario, quadro: Quadro, unidade: str) -> None:
    from .workflow import _exigir_configurar

    _exigir_configurar(db, ator, db.get(Espaco, quadro.espaco_id))
    if unidade not in UNIDADES_ESTIMATIVA:
        raise ErroDeRegra("Unidade inválida.")
    quadro.unidade_estimativa = unidade
    db.commit()
