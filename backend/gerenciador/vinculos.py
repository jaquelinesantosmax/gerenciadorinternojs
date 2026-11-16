"""Itens relacionados: sete tipos fixos, sempre bidirecionais e permitidos entre espaços diferentes.

Validações (docs/decisoes-de-desenho.md): sem vínculo com o próprio item, sem vínculo repetido e
aviso de bloqueio circular. Item em espaço sem acesso aparece só com a chave e a marca "acesso restrito".
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from . import relogio
from .erros import ErroDeRegra, NaoEncontrado, OperacaoNegada, SemPermissao
from .espacos import pode_no_espaco
from .modelos import Usuario
from .modelos_espacos import Espaco, StatusItem
from .modelos_itens import TIPOS_VINCULO, HistoricoItem, Item, Vinculo


class AvisoBloqueioCircular(OperacaoNegada):
    """O vínculo fecharia um ciclo de bloqueios. Pode ser criado se a pessoa confirmar."""


def _ja_existe(db: Session, tipo: str, origem: Item, destino: Item) -> bool:
    mesma_direcao = (Vinculo.origem_id == origem.id) & (Vinculo.destino_id == destino.id)
    inversa = (Vinculo.origem_id == destino.id) & (Vinculo.destino_id == origem.id)
    # "Relacionado a" é igual nos dois sentidos; nos demais, A bloqueia B e B bloqueia A são vínculos diferentes.
    condicao = or_(mesma_direcao, inversa) if tipo == "relacionado" else mesma_direcao
    return db.scalar(select(Vinculo.id).where(Vinculo.tipo == tipo, condicao)) is not None


def _fecha_ciclo_de_bloqueio(db: Session, origem: Item, destino: Item) -> bool:
    """origem bloqueia destino fecha um ciclo se destino já bloqueia origem, direta ou indiretamente."""
    visitados, fila = set(), [destino.id]
    while fila:
        atual = fila.pop()
        if atual == origem.id:
            return True
        if atual in visitados:
            continue
        visitados.add(atual)
        fila.extend(db.scalars(select(Vinculo.destino_id).where(Vinculo.tipo == "bloqueia", Vinculo.origem_id == atual)))
    return False


def _historico(db: Session, item: Item, autor: Usuario, antes: str | None, depois: str | None) -> None:
    db.add(HistoricoItem(item_id=item.id, autor_id=autor.id, ocorrido_em=relogio.agora(), campo="Itens relacionados",
                         valor_anterior=antes, valor_novo=depois))


def criar_vinculo_sistema(db: Session, ator: Usuario, tipo: str, origem: Item, destino: Item) -> Vinculo:
    vinculo = Vinculo(tipo=tipo, origem_id=origem.id, destino_id=destino.id, criado_por_id=ator.id,
                      criado_em=relogio.agora())
    db.add(vinculo)
    return vinculo


def criar(
    db: Session, ator: Usuario, item: Item, espaco: Espaco, tipo: str, sentido: str, outro: Item, outro_espaco: Espaco,
    confirmar_ciclo: bool = False,
) -> Vinculo:
    """sentido "saida": item <tipo> outro (ex.: item bloqueia outro). "entrada": outro <tipo> item."""
    from .itens import chave

    if tipo not in TIPOS_VINCULO:
        raise ErroDeRegra("Tipo de vínculo inválido.")
    if sentido not in ("saida", "entrada"):
        raise ErroDeRegra("Sentido do vínculo inválido.")
    if not pode_no_espaco(db, ator, espaco, "vincular"):
        raise SemPermissao("Você não tem permissão para vincular itens neste espaço.")
    if not pode_no_espaco(db, ator, outro_espaco, "ver"):
        raise NaoEncontrado("Item não encontrado.")
    if outro.id == item.id:
        raise OperacaoNegada("Um item não pode ser vinculado a ele mesmo.")
    origem, destino = (item, outro) if sentido == "saida" else (outro, item)
    if _ja_existe(db, tipo, origem, destino):
        raise OperacaoNegada("Esse vínculo já existe.")
    if tipo == "bloqueia" and not confirmar_ciclo and _fecha_ciclo_de_bloqueio(db, origem, destino):
        raise AvisoBloqueioCircular(
            "Este vínculo fecha um ciclo de bloqueios: os itens passam a bloquear uns aos outros. Criar mesmo assim?"
        )
    vinculo = criar_vinculo_sistema(db, ator, tipo, origem, destino)
    origem_esp = espaco if origem.id == item.id else outro_espaco
    destino_esp = espaco if destino.id == item.id else outro_espaco
    nome_ida, nome_volta = TIPOS_VINCULO[tipo]
    _historico(db, origem, ator, None, f"{nome_ida} {chave(destino_esp, destino)}")
    _historico(db, destino, ator, None, f"{nome_volta} {chave(origem_esp, origem)}")
    db.commit()
    return vinculo


def remover(db: Session, ator: Usuario, item: Item, espaco: Espaco, vinculo_id: uuid.UUID) -> None:
    from .itens import chave

    vinculo = db.get(Vinculo, vinculo_id)
    if vinculo is None or item.id not in (vinculo.origem_id, vinculo.destino_id):
        raise NaoEncontrado("Vínculo não encontrado.")
    if not pode_no_espaco(db, ator, espaco, "vincular"):
        raise SemPermissao("Você não tem permissão para desvincular itens neste espaço.")
    origem, destino = db.get(Item, vinculo.origem_id), db.get(Item, vinculo.destino_id)
    nome_ida, nome_volta = TIPOS_VINCULO[vinculo.tipo]
    esp_o, esp_d = db.get(Espaco, origem.espaco_id), db.get(Espaco, destino.espaco_id)
    _historico(db, origem, ator, f"{nome_ida} {chave(esp_d, destino)}", None)
    _historico(db, destino, ator, f"{nome_volta} {chave(esp_o, origem)}", None)
    db.delete(vinculo)
    db.commit()


@dataclass
class VinculoVisto:
    id: uuid.UUID
    tipo: str
    rotulo: str
    chave: str
    acesso_restrito: bool
    resumo: str | None
    status: str | None
    status_categoria: str | None
    bloqueio_aberto: bool  # este item é bloqueado por um item ainda não concluído


def listar(db: Session, viewer: Usuario, item: Item) -> list[VinculoVisto]:
    from .itens import chave

    vistos = []
    linhas = db.scalars(select(Vinculo).where(or_(Vinculo.origem_id == item.id, Vinculo.destino_id == item.id))
                        .order_by(Vinculo.criado_em))
    for v in linhas:
        sou_origem = v.origem_id == item.id
        outro = db.get(Item, v.destino_id if sou_origem else v.origem_id)
        if outro is None or outro.excluido_em is not None:
            continue
        esp = db.get(Espaco, outro.espaco_id)
        acesso = pode_no_espaco(db, viewer, esp, "ver")
        status = db.get(StatusItem, outro.status_id)
        rotulo = TIPOS_VINCULO[v.tipo][0 if sou_origem else 1]
        vistos.append(
            VinculoVisto(
                id=v.id, tipo=v.tipo, rotulo=rotulo, chave=chave(esp, outro), acesso_restrito=not acesso,
                resumo=outro.resumo if acesso else None,
                status=status.nome if acesso and status else None,
                status_categoria=status.categoria if acesso and status else None,
                # A informação de "ainda aberto" aparece mesmo sem acesso, sem revelar o conteúdo.
                bloqueio_aberto=(v.tipo == "bloqueia" and not sou_origem and status is not None
                                 and status.categoria != "concluido"),
            )
        )
    return vistos


def bloqueios_abertos(db: Session, viewer: Usuario, item: Item) -> list[str]:
    """Chaves dos itens que ainda bloqueiam este (usado para o alerta ao concluir, na Etapa 3)."""
    return [v.chave for v in listar(db, viewer, item) if v.bloqueio_aberto]
