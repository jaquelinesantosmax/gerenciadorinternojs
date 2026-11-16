"""Preenche dados que dependem das regras do sistema, depois das migrações. Pode rodar quantas vezes quiser:
só completa o que falta.

- Espaços sem status ligados ganham os 8 status padrão, o fluxo padrão e o quadro do modelo.
- Painéis sem quadro ganham o quadro próprio.
- Itens sem histórico de status ganham o histórico refeito a partir do histórico do item (para as métricas).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .modelos_espacos import Espaco, Painel, StatusItem
from .modelos_itens import HistoricoItem, Item
from .modelos_quadros import Quadro, StatusDoEspaco
from .modelos_scrum import MudancaStatus
from .workflow import preparar_espaco, preparar_painel


def preparar(db: Session) -> dict[str, int]:
    contagem = {"espacos": 0, "paineis": 0, "itens": 0}
    com_status = set(db.scalars(select(StatusDoEspaco.espaco_id).distinct()))
    for espaco in db.scalars(select(Espaco)).all():
        if espaco.id not in com_status:
            preparar_espaco(db, espaco)
            contagem["espacos"] += 1
    db.flush()
    com_quadro = set(db.scalars(select(Quadro.painel_id).where(Quadro.painel_id.is_not(None))))
    for painel in db.scalars(select(Painel)).all():
        if painel.id not in com_quadro:
            preparar_painel(db, db.get(Espaco, painel.espaco_id), painel)
            contagem["paineis"] += 1

    com_historico = set(db.scalars(select(MudancaStatus.item_id).distinct()))
    todos = list(db.scalars(select(StatusItem)))
    for item in db.scalars(select(Item)).all():
        if item.id in com_historico:
            continue
        nomes = {s.nome: s for s in todos if s.espaco_id in (None, item.espaco_id)}
        mudancas = list(db.scalars(select(HistoricoItem).where(HistoricoItem.item_id == item.id, HistoricoItem.campo == "Status")
                                   .order_by(HistoricoItem.ocorrido_em)))
        inicial = nomes.get(mudancas[0].valor_anterior) if mudancas else db.get(StatusItem, item.status_id)
        if inicial is not None:
            db.add(MudancaStatus(item_id=item.id, de_status_id=None, para_status_id=inicial.id,
                                 categoria=inicial.categoria, quando=item.criado_em))
        anterior = inicial
        for h in mudancas:
            novo = nomes.get((h.valor_novo or "").split(" (")[0])
            if novo is None:
                continue
            db.add(MudancaStatus(item_id=item.id, de_status_id=anterior.id if anterior else None, para_status_id=novo.id,
                                 categoria=novo.categoria, quando=h.ocorrido_em))
            anterior = novo
        contagem["itens"] += 1
    db.commit()
    return contagem
