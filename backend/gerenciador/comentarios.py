"""Comentários: mesmo editor de texto formatado da descrição.

- Comentário editado mostra a marca "editado" e a versão anterior fica guardada.
- Comentário excluído deixa a linha "comentário excluído por fulano em tal data".
- Editar ou excluir: o ADM do espaço pode em qualquer comentário; os demais, só nos próprios.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import relogio, texto_rico
from .auditoria import TipoEvento, registrar
from .erros import ErroDeRegra, NaoEncontrado, OperacaoNegada, SemPermissao
from .espacos import pode_no_espaco
from .modelos import Usuario
from .modelos_espacos import Espaco
from .modelos_itens import Anexo, Comentario, Item, VersaoComentario


def _anexos(db: Session, item: Item) -> set[uuid.UUID]:
    return set(db.scalars(select(Anexo.id).where(Anexo.item_id == item.id, Anexo.excluido_em.is_(None))))


def _corpo(db: Session, item: Item, corpo: Any) -> dict:
    limpo = texto_rico.validar(corpo, _anexos(db, item))
    if limpo is None:
        raise ErroDeRegra("Escreva algo antes de enviar.")
    return limpo


def criar(db: Session, ator: Usuario, item: Item, espaco: Espaco, corpo: Any) -> Comentario:
    if not pode_no_espaco(db, ator, espaco, "comentar"):
        raise SemPermissao("Você não tem permissão para comentar neste espaço.")
    comentario = Comentario(item_id=item.id, autor_id=ator.id, corpo=_corpo(db, item, corpo), criado_em=relogio.agora())
    db.add(comentario)
    db.commit()
    return comentario


def _buscar(db: Session, item: Item, comentario_id: uuid.UUID) -> Comentario:
    comentario = db.get(Comentario, comentario_id)
    if comentario is None or comentario.item_id != item.id:
        raise NaoEncontrado("Comentário não encontrado.")
    if comentario.excluido_em is not None:
        raise OperacaoNegada("Este comentário foi excluído.")
    return comentario


def _pode_mexer(db: Session, ator: Usuario, espaco: Espaco, comentario: Comentario) -> bool:
    if pode_no_espaco(db, ator, espaco, "editar_qualquer_comentario"):
        return True
    return comentario.autor_id == ator.id and pode_no_espaco(db, ator, espaco, "comentar")


def editar(db: Session, ator: Usuario, item: Item, espaco: Espaco, comentario_id: uuid.UUID, corpo: Any) -> Comentario:
    comentario = _buscar(db, item, comentario_id)
    if not _pode_mexer(db, ator, espaco, comentario):
        raise SemPermissao("Você só pode editar os seus comentários.")
    novo = _corpo(db, item, corpo)
    if novo == comentario.corpo:
        return comentario
    agora = relogio.agora()
    db.add(VersaoComentario(comentario_id=comentario.id, corpo=comentario.corpo, substituido_em=agora))
    comentario.corpo = novo
    comentario.editado_em = agora
    db.commit()
    return comentario


def excluir(
    db: Session, ator: Usuario, item: Item, espaco: Espaco, comentario_id: uuid.UUID, ip: str | None
) -> None:
    comentario = _buscar(db, item, comentario_id)
    if not _pode_mexer(db, ator, espaco, comentario):
        raise SemPermissao("Você só pode excluir os seus comentários.")
    comentario.excluido_em = relogio.agora()
    comentario.excluido_por_id = ator.id
    registrar(db, TipoEvento.COMENTARIO_EXCLUIDO, ator_id=ator.id, alvo_usuario_id=comentario.autor_id, ip=ip,
              item=f"{espaco.sigla}-{item.numero}")
    db.commit()


def listar(db: Session, item: Item) -> list[Comentario]:
    return list(db.scalars(select(Comentario).where(Comentario.item_id == item.id).order_by(Comentario.criado_em.desc())))


def versoes(db: Session, comentario: Comentario) -> list[VersaoComentario]:
    return list(db.scalars(select(VersaoComentario).where(VersaoComentario.comentario_id == comentario.id)
                           .order_by(VersaoComentario.substituido_em.desc())))
