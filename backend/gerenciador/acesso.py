"""Etapa 4: acesso por time, Gestor que acompanha, suporte do ADM da plataforma, Solicitar acesso,
espaço aberto e compartilhamento do espaço pessoal (docs/matriz-de-permissoes.md)."""

import uuid
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import relogio
from .auditoria import TipoEvento, registrar
from .erros import ErroDeRegra, NaoEncontrado, OperacaoNegada, SemPermissao
from .espacos import NOME_PAPEL_ESPACO, _contar_adms, papel_de_membro, pode_no_espaco
from .modelos import Usuario
from .modelos_acesso import AcessoTime, Compartilhamento, GestorAcompanha, PedidoAcesso, SessaoSuporte
from .modelos_espacos import PAPEIS_ESPACO, Espaco, MembroEspaco, TimeProvisorio
from .papeis import ADM, GESTOR, papeis_ativos

DURACAO_SUPORTE = timedelta(hours=4)


def _exigir(db: Session, ator: Usuario, espaco: Espaco, acao: str) -> None:
    if not pode_no_espaco(db, ator, espaco, acao):
        raise SemPermissao("Você não tem permissão para esta ação.")


def _papel(papel: str) -> str:
    if papel not in PAPEIS_ESPACO:
        raise ErroDeRegra("Papel inválido.")
    return papel


# --- Acesso de times a espaços ----------------------------------------------------------------

def acessos_de_time(db: Session, espaco: Espaco) -> list[tuple[AcessoTime, TimeProvisorio]]:
    return list(db.execute(select(AcessoTime, TimeProvisorio).join(TimeProvisorio, TimeProvisorio.id == AcessoTime.time_id)
                           .where(AcessoTime.espaco_id == espaco.id).order_by(TimeProvisorio.nome)).all())


def dar_acesso_time(db: Session, ator: Usuario, espaco: Espaco, time_id: uuid.UUID, papel: str, ip: str | None) -> None:
    if espaco.tipo != "projeto":
        raise OperacaoNegada("Só espaços de projeto recebem times.")
    _exigir(db, ator, espaco, "gerenciar_membros")
    time = db.get(TimeProvisorio, time_id)
    if time is None or not time.ativo:
        raise NaoEncontrado("Time não encontrado.")
    existente = db.scalar(select(AcessoTime).where(AcessoTime.espaco_id == espaco.id, AcessoTime.time_id == time.id))
    if existente is not None:
        raise OperacaoNegada(f"O time {time.nome} já tem acesso como {NOME_PAPEL_ESPACO[existente.papel]}.")
    db.add(AcessoTime(espaco_id=espaco.id, time_id=time.id, papel=_papel(papel), adicionado_por_id=ator.id,
                      adicionado_em=relogio.agora()))
    registrar(db, TipoEvento.TIME_ACESSO_DADO, ator_id=ator.id, ip=ip, espaco=espaco.sigla, time=time.nome, papel=papel)
    db.commit()


def _acesso(db: Session, espaco: Espaco, time_id: uuid.UUID) -> AcessoTime:
    acesso = db.scalar(select(AcessoTime).where(AcessoTime.espaco_id == espaco.id, AcessoTime.time_id == time_id))
    if acesso is None:
        raise NaoEncontrado("Esse time não tem acesso a este espaço.")
    return acesso


def mudar_acesso_time(db: Session, ator: Usuario, espaco: Espaco, time_id: uuid.UUID, papel: str, ip: str | None) -> None:
    _exigir(db, ator, espaco, "gerenciar_membros")
    acesso = _acesso(db, espaco, time_id)
    anterior = acesso.papel
    acesso.papel = _papel(papel)
    db.flush()
    if anterior == "adm" and _contar_adms(db, espaco) < 1:
        db.rollback()
        raise OperacaoNegada("O espaço precisa ter pelo menos um ADM.")
    registrar(db, TipoEvento.TIME_ACESSO_ALTERADO, ator_id=ator.id, ip=ip, espaco=espaco.sigla,
              time=db.get(TimeProvisorio, time_id).nome, de=anterior, para=papel)
    db.commit()


def tirar_acesso_time(db: Session, ator: Usuario, espaco: Espaco, time_id: uuid.UUID, ip: str | None) -> None:
    _exigir(db, ator, espaco, "gerenciar_membros")
    acesso = _acesso(db, espaco, time_id)
    db.delete(acesso)
    db.flush()
    if acesso.papel == "adm" and _contar_adms(db, espaco) < 1:
        db.rollback()
        raise OperacaoNegada("O espaço precisa ter pelo menos um ADM.")
    registrar(db, TipoEvento.TIME_ACESSO_RETIRADO, ator_id=ator.id, ip=ip, espaco=espaco.sigla,
              time=db.get(TimeProvisorio, time_id).nome)
    db.commit()


# --- Gestor -----------------------------------------------------------------------------------

def acompanhar(db: Session, ator: Usuario, espaco: Espaco, sim: bool) -> None:
    """Gestor escolhe os espaços de equipe que acompanha (vão para o Espaço da Gestão, na Etapa 7)."""
    if GESTOR not in papeis_ativos(db, ator.id):
        raise SemPermissao("Só Gestores acompanham espaços.")
    if espaco.tipo != "projeto":
        raise OperacaoNegada("Espaços pessoais ficam fora do alcance do Gestor.")
    existente = db.scalar(select(GestorAcompanha).where(GestorAcompanha.usuario_id == ator.id,
                                                        GestorAcompanha.espaco_id == espaco.id))
    if sim and existente is None:
        db.add(GestorAcompanha(usuario_id=ator.id, espaco_id=espaco.id, desde=relogio.agora()))
    elif not sim and existente is not None:
        db.delete(existente)
    db.commit()


def acompanha(db: Session, usuario: Usuario, espaco: Espaco) -> bool:
    return db.scalar(select(GestorAcompanha.id).where(GestorAcompanha.usuario_id == usuario.id,
                                                      GestorAcompanha.espaco_id == espaco.id)) is not None


def gestores_do_espaco(db: Session, ator: Usuario, espaco: Espaco) -> list[tuple[Usuario, GestorAcompanha]]:
    _exigir(db, ator, espaco, "ver_gestores")
    linhas = db.execute(select(Usuario, GestorAcompanha).join(GestorAcompanha, GestorAcompanha.usuario_id == Usuario.id)
                        .where(GestorAcompanha.espaco_id == espaco.id).order_by(Usuario.nome)).all()
    # Só quem ainda é Gestor e está ativo.
    return [(u, g) for u, g in linhas if u.ativo and GESTOR in papeis_ativos(db, u.id)]


# --- Suporte do ADM da plataforma -------------------------------------------------------------

def sessao_suporte(db: Session, usuario: Usuario, espaco: Espaco) -> SessaoSuporte | None:
    return db.scalar(select(SessaoSuporte).where(
        SessaoSuporte.usuario_id == usuario.id, SessaoSuporte.espaco_id == espaco.id,
        SessaoSuporte.encerrada_em.is_(None), SessaoSuporte.expira_em > relogio.agora()))


def entrar_suporte(db: Session, ator: Usuario, espaco: Espaco, motivo: str, ip: str | None) -> SessaoSuporte:
    if ADM not in papeis_ativos(db, ator.id):
        raise SemPermissao("Só o ADM da plataforma entra em espaços para suporte.")
    if espaco.tipo != "projeto":
        raise OperacaoNegada("Espaços pessoais ficam fora do alcance do suporte.")
    motivo = (motivo or "").strip()
    if not motivo:
        raise ErroDeRegra("Informe o motivo do suporte.")
    atual = sessao_suporte(db, ator, espaco)
    if atual is not None:
        return atual
    agora = relogio.agora()
    sessao = SessaoSuporte(usuario_id=ator.id, espaco_id=espaco.id, motivo=motivo[:2000], inicio=agora,
                           expira_em=agora + DURACAO_SUPORTE)
    db.add(sessao)
    registrar(db, TipoEvento.SUPORTE_INICIADO, ator_id=ator.id, ip=ip, espaco=espaco.sigla, motivo=motivo[:500],
              expira_em=sessao.expira_em.isoformat())
    db.commit()
    return sessao


def sair_suporte(db: Session, ator: Usuario, espaco: Espaco, ip: str | None) -> None:
    sessao = sessao_suporte(db, ator, espaco)
    if sessao is None:
        raise OperacaoNegada("Você não está em suporte neste espaço.")
    sessao.encerrada_em = relogio.agora()
    registrar(db, TipoEvento.SUPORTE_ENCERRADO, ator_id=ator.id, ip=ip, espaco=espaco.sigla)
    db.commit()


def espacos_em_suporte(db: Session, usuario: Usuario) -> list[uuid.UUID]:
    return list(db.scalars(select(SessaoSuporte.espaco_id).where(
        SessaoSuporte.usuario_id == usuario.id, SessaoSuporte.encerrada_em.is_(None),
        SessaoSuporte.expira_em > relogio.agora())))


# --- Solicitar acesso -------------------------------------------------------------------------

def pedido_pendente(db: Session, usuario: Usuario, espaco: Espaco) -> PedidoAcesso | None:
    return db.scalar(select(PedidoAcesso).where(PedidoAcesso.espaco_id == espaco.id, PedidoAcesso.usuario_id == usuario.id,
                                                PedidoAcesso.estado == "pendente"))


def solicitar(db: Session, ator: Usuario, espaco: Espaco, item_chave: str | None, mensagem: str | None) -> PedidoAcesso:
    if espaco.tipo != "projeto":
        raise OperacaoNegada("Espaços pessoais não recebem pedidos de acesso.")
    papel = papel_de_membro(db, ator, espaco)
    if papel in ("adm", "membro"):
        raise OperacaoNegada(f"Você já é {NOME_PAPEL_ESPACO[papel]} deste espaço.")
    pendente = pedido_pendente(db, ator, espaco)
    if pendente is not None:
        return pendente
    pedido = PedidoAcesso(espaco_id=espaco.id, usuario_id=ator.id, item_chave=item_chave,
                          mensagem=(mensagem or "").strip()[:1000] or None, criado_em=relogio.agora(), estado="pendente")
    db.add(pedido)
    db.commit()
    return pedido


def pedidos_pendentes(db: Session, ator: Usuario, espaco: Espaco) -> list[PedidoAcesso]:
    _exigir(db, ator, espaco, "aprovar_acesso")
    return list(db.scalars(select(PedidoAcesso).where(PedidoAcesso.espaco_id == espaco.id, PedidoAcesso.estado == "pendente")
                           .order_by(PedidoAcesso.criado_em)))


def _pedido(db: Session, espaco: Espaco, pedido_id: uuid.UUID) -> PedidoAcesso:
    pedido = db.get(PedidoAcesso, pedido_id)
    if pedido is None or pedido.espaco_id != espaco.id:
        raise NaoEncontrado("Pedido não encontrado.")
    if pedido.estado != "pendente":
        raise OperacaoNegada("Esse pedido já foi respondido.")
    return pedido


def aprovar(db: Session, ator: Usuario, espaco: Espaco, pedido_id: uuid.UUID, papel: str, ip: str | None) -> None:
    """Quem aprova escolhe o papel; não há papel pré-selecionado (docs/decisoes-de-desenho.md)."""
    _exigir(db, ator, espaco, "aprovar_acesso")
    pedido = _pedido(db, espaco, pedido_id)
    papel = _papel(papel)
    alvo = db.get(Usuario, pedido.usuario_id)
    if not alvo.ativo:
        raise OperacaoNegada(f"{alvo.nome} está desativado.")
    membro = db.scalar(select(MembroEspaco).where(MembroEspaco.espaco_id == espaco.id, MembroEspaco.usuario_id == alvo.id))
    agora = relogio.agora()
    if membro is None:
        db.add(MembroEspaco(espaco_id=espaco.id, usuario_id=alvo.id, papel=papel, adicionado_por_id=ator.id, adicionado_em=agora))
        registrar(db, TipoEvento.MEMBRO_ADICIONADO, ator_id=ator.id, alvo_usuario_id=alvo.id, ip=ip, espaco=espaco.sigla,
                  papel=papel, por_pedido=True)
    elif membro.papel != papel:
        anterior, membro.papel = membro.papel, papel
        registrar(db, TipoEvento.MEMBRO_PAPEL_ALTERADO, ator_id=ator.id, alvo_usuario_id=alvo.id, ip=ip,
                  espaco=espaco.sigla, de=anterior, para=papel, por_pedido=True)
    pedido.estado, pedido.papel, pedido.decidido_por_id, pedido.decidido_em = "aprovado", papel, ator.id, agora
    db.commit()


def recusar(db: Session, ator: Usuario, espaco: Espaco, pedido_id: uuid.UUID, ip: str | None) -> None:
    _exigir(db, ator, espaco, "aprovar_acesso")
    pedido = _pedido(db, espaco, pedido_id)
    pedido.estado, pedido.decidido_por_id, pedido.decidido_em = "recusado", ator.id, relogio.agora()
    registrar(db, TipoEvento.PEDIDO_ACESSO_RECUSADO, ator_id=ator.id, alvo_usuario_id=pedido.usuario_id, ip=ip,
              espaco=espaco.sigla)
    db.commit()


# --- Espaço aberto e compartilhamento do pessoal ----------------------------------------------

def marcar_aberto(db: Session, ator: Usuario, espaco: Espaco, aberto: bool, ip: str | None) -> None:
    if espaco.tipo != "projeto":
        raise OperacaoNegada("Só espaços de projeto podem ser abertos para a empresa.")
    _exigir(db, ator, espaco, "marcar_aberto")
    if espaco.aberto == aberto:
        return
    espaco.aberto = aberto
    registrar(db, TipoEvento.ESPACO_ABERTO if aberto else TipoEvento.ESPACO_FECHADO, ator_id=ator.id, ip=ip,
              espaco=espaco.sigla)
    db.commit()


def compartilhamentos(db: Session, espaco: Espaco) -> list[tuple[Usuario, Compartilhamento]]:
    return list(db.execute(select(Usuario, Compartilhamento).join(Compartilhamento, Compartilhamento.usuario_id == Usuario.id)
                           .where(Compartilhamento.espaco_id == espaco.id).order_by(Usuario.nome)).all())


def compartilhar(db: Session, ator: Usuario, espaco: Espaco, usuario_id: uuid.UUID) -> None:
    """Espaço pessoal: compartilhamento sempre só leitura (decisão de 16/11)."""
    if espaco.tipo != "pessoal":
        raise OperacaoNegada("Só espaços pessoais são compartilhados assim. Em espaços de projeto, use os membros.")
    _exigir(db, ator, espaco, "compartilhar")
    alvo = db.get(Usuario, usuario_id)
    if alvo is None or not alvo.ativo:
        raise NaoEncontrado("Pessoa não encontrada.")
    if alvo.id == ator.id:
        raise OperacaoNegada("O espaço já é seu.")
    if db.scalar(select(Compartilhamento.id).where(Compartilhamento.espaco_id == espaco.id,
                                                   Compartilhamento.usuario_id == alvo.id)):
        raise OperacaoNegada(f"O espaço já está compartilhado com {alvo.nome}.")
    db.add(Compartilhamento(espaco_id=espaco.id, usuario_id=alvo.id, criado_em=relogio.agora()))
    db.commit()


def descompartilhar(db: Session, ator: Usuario, espaco: Espaco, usuario_id: uuid.UUID) -> None:
    _exigir(db, ator, espaco, "compartilhar")
    existente = db.scalar(select(Compartilhamento).where(Compartilhamento.espaco_id == espaco.id,
                                                         Compartilhamento.usuario_id == usuario_id))
    if existente is None:
        raise NaoEncontrado("Esse compartilhamento não existe.")
    db.delete(existente)
    db.commit()
