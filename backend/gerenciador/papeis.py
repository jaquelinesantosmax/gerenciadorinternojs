"""Papéis da plataforma e o que cada um pode fazer (docs/matriz-de-permissoes.md, seção Plataforma)."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from . import relogio
from .auditoria import TipoEvento, registrar
from .erros import NaoEncontrado, OperacaoNegada, SemPermissao
from .identidade import dominio_autorizado, normalizar_email
from .modelos import ConcessaoPapel, Papel, Usuario

ADM = Papel.ADM_PLATAFORMA
GESTOR = Papel.GESTOR
CRIAR = Papel.CRIAR_ESPACOS

# Cada permissão da matriz e os papéis que a têm. Só entram aqui as que já existem no sistema.
PERMISSOES: dict[str, frozenset[Papel]] = {
    "configurar_dominios": frozenset({ADM}),
    "dar_tirar_adm_plataforma": frozenset({ADM}),
    "dar_tirar_gestor": frozenset({ADM, GESTOR}),
    "dar_tirar_criar_espacos": frozenset({ADM, GESTOR}),
    "desativar_usuarios": frozenset({ADM}),
    "ver_auditoria": frozenset({ADM, GESTOR}),
    "ver_usuarios": frozenset({ADM, GESTOR}),
    "criar_espaco_equipe": frozenset({ADM, GESTOR, CRIAR}),
    "acessar_espaco_gestao": frozenset({ADM, GESTOR}),
    # Lista provisória de Times (decisão de 16/11), até o cadastro de Times da Etapa 4.
    "gerenciar_times_provisorios": frozenset({ADM}),
    "definir_limite_anexos": frozenset({ADM}),
}

_PERMISSAO_PARA_PAPEL = {
    ADM: "dar_tirar_adm_plataforma",
    GESTOR: "dar_tirar_gestor",
    CRIAR: "dar_tirar_criar_espacos",
}

NOMES = {ADM: "ADM da plataforma", GESTOR: "Gestor", CRIAR: "Criar espaços"}

_TRAVA_ADMS = 7_100_001  # identificador fixo da trava usada em contar_adms_ativos


def papeis_ativos(db: Session, usuario_id: uuid.UUID) -> set[Papel]:
    linhas = db.scalars(
        select(ConcessaoPapel.papel).where(
            ConcessaoPapel.usuario_id == usuario_id, ConcessaoPapel.revogado_em.is_(None)
        )
    )
    return {Papel(p) for p in linhas}


def permissoes_de(papeis: set[Papel]) -> dict[str, bool]:
    return {nome: bool(papeis & quem) for nome, quem in PERMISSOES.items()}


def pode(db: Session, usuario: Usuario, permissao: str) -> bool:
    return usuario.ativo and bool(papeis_ativos(db, usuario.id) & PERMISSOES[permissao])


def exigir(db: Session, usuario: Usuario, permissao: str) -> None:
    if not pode(db, usuario, permissao):
        raise SemPermissao("Você não tem permissão para esta ação.")


def contar_adms_ativos(db: Session) -> int:
    """Conta os ADMs ativos. Trava a contagem até o fim da transação, para dois ADMs que se tiram
    ao mesmo tempo não deixarem a plataforma sem nenhum."""
    db.execute(text("SELECT pg_advisory_xact_lock(:chave)"), {"chave": _TRAVA_ADMS})
    return db.scalar(
        select(func.count())
        .select_from(ConcessaoPapel)
        .join(Usuario, Usuario.id == ConcessaoPapel.usuario_id)
        .where(ConcessaoPapel.papel == ADM.value, ConcessaoPapel.revogado_em.is_(None), Usuario.ativo)
    ) or 0


def _concessao_ativa(db: Session, usuario_id: uuid.UUID, papel: Papel) -> ConcessaoPapel | None:
    return db.scalar(
        select(ConcessaoPapel).where(
            ConcessaoPapel.usuario_id == usuario_id,
            ConcessaoPapel.papel == papel.value,
            ConcessaoPapel.revogado_em.is_(None),
        )
    )


def _buscar_usuario(db: Session, usuario_id: uuid.UUID) -> Usuario:
    usuario = db.get(Usuario, usuario_id)
    if usuario is None:
        raise NaoEncontrado("Usuário não encontrado.")
    return usuario


def conceder(db: Session, ator: Usuario, alvo_id: uuid.UUID, papel: Papel, ip: str | None) -> None:
    exigir(db, ator, _PERMISSAO_PARA_PAPEL[papel])
    alvo = _buscar_usuario(db, alvo_id)
    if not alvo.ativo:
        raise OperacaoNegada("Reative o usuário antes de dar um papel a ele.")
    if _concessao_ativa(db, alvo.id, papel) is not None:
        raise OperacaoNegada(f"{alvo.nome} já tem o papel {NOMES[papel]}.")
    db.add(
        ConcessaoPapel(usuario_id=alvo.id, papel=papel.value, concedido_por_id=ator.id,
                       concedido_em=relogio.agora())
    )
    registrar(db, TipoEvento.PAPEL_CONCEDIDO, ator_id=ator.id, alvo_usuario_id=alvo.id, ip=ip,
              papel=papel.value)
    db.commit()


def revogar(db: Session, ator: Usuario, alvo_id: uuid.UUID, papel: Papel, ip: str | None) -> None:
    exigir(db, ator, _PERMISSAO_PARA_PAPEL[papel])
    alvo = _buscar_usuario(db, alvo_id)
    concessao = _concessao_ativa(db, alvo.id, papel)
    if concessao is None:
        raise OperacaoNegada(f"{alvo.nome} não tem o papel {NOMES[papel]}.")
    if papel == ADM and alvo.ativo and contar_adms_ativos(db) <= 1:
        raise OperacaoNegada("A plataforma precisa ter pelo menos um ADM da plataforma.")
    concessao.revogado_em = relogio.agora()
    concessao.revogado_por_id = ator.id
    registrar(db, TipoEvento.PAPEL_REVOGADO, ator_id=ator.id, alvo_usuario_id=alvo.id, ip=ip,
              papel=papel.value)
    db.commit()


@dataclass
class GestorAtivo:
    usuario: Usuario
    concedido_por: Usuario | None
    concedido_em: datetime


def listar_gestores(db: Session) -> list[GestorAtivo]:
    concessoes = db.scalars(
        select(ConcessaoPapel)
        .where(ConcessaoPapel.papel == GESTOR.value, ConcessaoPapel.revogado_em.is_(None))
        .order_by(ConcessaoPapel.concedido_em.desc())
    )
    return [GestorAtivo(c.usuario, c.concedido_por, c.concedido_em) for c in concessoes]


def cadastrar_adm_instalacao(db: Session, email: str, nome: str) -> Usuario:
    """Cadastro manual do primeiro ADM da plataforma, feito na instalação (pela linha de comando)."""
    email = normalizar_email(email)
    if not dominio_autorizado(db, email):
        raise OperacaoNegada("O e-mail precisa ser de um domínio autorizado (jusbrasil.com.br ou digesto.com.br).")
    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    agora = relogio.agora()
    if usuario is None:
        if not nome.strip():
            raise OperacaoNegada("Informe o nome.")
        usuario = Usuario(email=email, nome=nome.strip(), criado_em=agora)
        db.add(usuario)
        db.flush()
    if _concessao_ativa(db, usuario.id, ADM) is None:
        db.add(ConcessaoPapel(usuario_id=usuario.id, papel=ADM.value, concedido_por_id=None, concedido_em=agora))
        registrar(db, TipoEvento.ADM_INSTALACAO, alvo_usuario_id=usuario.id, papel=ADM.value)
    db.commit()
    return usuario
