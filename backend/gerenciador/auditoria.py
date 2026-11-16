"""Registro de auditoria. Cada evento guarda quem fez, sobre quem, quando e de onde."""

import enum
import uuid
from typing import Any

from sqlalchemy.orm import Session

from . import relogio
from .modelos import EventoAuditoria


class TipoEvento(str, enum.Enum):
    LOGIN = "login"
    LOGIN_FALHA = "login_falha"
    LOGOUT = "logout"
    CADASTRO_AUTOMATICO = "cadastro_automatico"
    ADM_INSTALACAO = "adm_instalacao"
    PAPEL_CONCEDIDO = "papel_concedido"
    PAPEL_REVOGADO = "papel_revogado"
    USUARIO_DESATIVADO = "usuario_desativado"
    USUARIO_REATIVADO = "usuario_reativado"
    DOMINIO_ADICIONADO = "dominio_adicionado"
    DOMINIO_REMOVIDO = "dominio_removido"
    ESPACO_CRIADO = "espaco_criado"
    MEMBRO_ADICIONADO = "membro_adicionado"
    MEMBRO_PAPEL_ALTERADO = "membro_papel_alterado"
    MEMBRO_REMOVIDO = "membro_removido"
    ITEM_EXCLUIDO = "item_excluido"
    CONCLUSAO_COM_BLOQUEIO = "conclusao_com_bloqueio"
    ANEXO_EXCLUIDO = "anexo_excluido"
    COMENTARIO_EXCLUIDO = "comentario_excluido"
    TIME_CRIADO = "time_criado"
    LIMITE_ANEXOS_ALTERADO = "limite_anexos_alterado"


def registrar(
    db: Session,
    tipo: TipoEvento,
    *,
    ator_id: uuid.UUID | None = None,
    alvo_usuario_id: uuid.UUID | None = None,
    ip: str | None = None,
    **detalhes: Any,
) -> EventoAuditoria:
    """Adiciona o evento à transação atual. Quem chama é responsável pelo commit."""
    evento = EventoAuditoria(
        ocorrido_em=relogio.agora(),
        tipo=tipo.value,
        ator_id=ator_id,
        alvo_usuario_id=alvo_usuario_id,
        ip=ip,
        detalhes=detalhes,
    )
    db.add(evento)
    return evento
