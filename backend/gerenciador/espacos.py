"""Espaços, membros, painéis, tipos de item próprios e opções de origem.

Papéis no espaço de projeto (docs/matriz-de-permissoes.md): ADM do espaço, Membro e Leitor.
No espaço pessoal, só o dono tem acesso (compartilhamento só leitura chega na Etapa 4).
"""

import re
import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import relogio
from .auditoria import TipoEvento, registrar
from .erros import NaoEncontrado, OperacaoNegada, SemPermissao
from .modelos import Usuario
from .modelos_espacos import (
    MODELOS_PROJETO,
    PAPEIS_ESPACO,
    Espaco,
    MembroEspaco,
    OpcaoOrigem,
    Painel,
    StatusItem,
    TipoItem,
)
from .papeis import exigir as exigir_plataforma

_SIGLA = re.compile(r"^[A-Z]{2,10}$")

NOME_PAPEL_ESPACO = {
    "adm": "ADM do espaço", "membro": "Membro", "leitor": "Leitor", "dono": "Dono", "gestor": "Gestor",
    "suporte": "Suporte (ADM da plataforma)", "aberto": "Leitura (espaço aberto)", "compartilhado": "Compartilhado com você",
}

# Matriz do espaço de projeto (docs/matriz-de-permissoes.md). Cada ação e quem pode fazer.
# "dono": dono do espaço pessoal. "compartilhado": pessoa com quem o espaço pessoal foi compartilhado (só leitura).
# "suporte": ADM da plataforma em suporte, com poderes de ADM do espaço (decisão de 16/11).
# "aberto": qualquer pessoa da empresa num espaço marcado como aberto.
# Regras de "só os próprios" (excluir itens, comentários e anexos) ficam nos módulos de cada coisa.
_ADM = {"adm", "suporte", "dono"}
ACOES_ESPACO: dict[str, frozenset[str]] = {
    "ver": frozenset(_ADM | {"membro", "leitor", "gestor", "aberto", "compartilhado"}),
    "criar_itens": frozenset(_ADM | {"membro", "gestor"}),
    "editar_itens": frozenset(_ADM | {"membro", "gestor"}),
    "comentar": frozenset(_ADM | {"membro", "leitor", "gestor", "aberto"}),
    "anexar": frozenset(_ADM | {"membro", "leitor", "gestor", "aberto"}),
    "vincular": frozenset(_ADM | {"membro", "gestor"}),
    "excluir_qualquer_item": frozenset(_ADM),
    "excluir_proprios_itens": frozenset(_ADM | {"membro", "gestor"}),
    "excluir_qualquer_anexo": frozenset(_ADM),
    "editar_qualquer_comentario": frozenset(_ADM),
    "configurar": frozenset(_ADM | {"gestor"}),
    "gerenciar_membros": frozenset({"adm", "suporte", "gestor"}),
    "aprovar_acesso": frozenset({"adm", "suporte", "gestor"}),
    "marcar_aberto": frozenset({"adm", "suporte"}),
    "ver_gestores": frozenset({"adm", "suporte", "membro"}),
    "criar_paineis": frozenset({"adm", "suporte", "gestor"}),
    "gerenciar_sprints": frozenset({"adm", "suporte", "membro", "dono"}),
    "compartilhar": frozenset({"dono"}),
}

# Ordem de força, para mostrar um papel só e para a regra "vale o maior" (decisão de 16/11).
_FORCA = ["dono", "adm", "suporte", "gestor", "membro", "leitor", "aberto", "compartilhado"]
_FORCA_MEMBRO = {"adm": 3, "membro": 2, "leitor": 1}


def papel_de_membro(db: Session, usuario: Usuario, espaco: Espaco) -> str | None:
    """Papel dado à pessoa (direto ou por time). Se houver mais de um, vale o maior."""
    from .modelos_acesso import AcessoTime, MembroTime

    papeis = set(db.scalars(select(MembroEspaco.papel).where(MembroEspaco.espaco_id == espaco.id,
                                                             MembroEspaco.usuario_id == usuario.id)))
    papeis |= set(db.scalars(
        select(AcessoTime.papel).join(MembroTime, MembroTime.time_id == AcessoTime.time_id)
        .where(AcessoTime.espaco_id == espaco.id, MembroTime.usuario_id == usuario.id)
    ))
    return max(papeis, key=lambda p: _FORCA_MEMBRO[p]) if papeis else None


def papeis_no_espaco(db: Session, usuario: Usuario, espaco: Espaco) -> set[str]:
    from .modelos_acesso import Compartilhamento, SessaoSuporte
    from .papeis import GESTOR, papeis_ativos

    if not usuario.ativo:
        return set()
    if espaco.tipo == "pessoal":
        # Espaço pessoal fica fora do alcance do Gestor e do suporte do ADM da plataforma.
        if espaco.dono_id == usuario.id:
            return {"dono"}
        compartilhado = db.scalar(select(Compartilhamento.id).where(Compartilhamento.espaco_id == espaco.id,
                                                                    Compartilhamento.usuario_id == usuario.id))
        return {"compartilhado"} if compartilhado else set()
    papeis: set[str] = set()
    membro = papel_de_membro(db, usuario, espaco)
    if membro:
        papeis.add(membro)
    if GESTOR in papeis_ativos(db, usuario.id):
        papeis.add("gestor")
    suporte = db.scalar(select(SessaoSuporte.id).where(
        SessaoSuporte.usuario_id == usuario.id, SessaoSuporte.espaco_id == espaco.id,
        SessaoSuporte.encerrada_em.is_(None), SessaoSuporte.expira_em > relogio.agora()))
    if suporte:
        papeis.add("suporte")
    if espaco.aberto:
        papeis.add("aberto")
    return papeis


def papel_no_espaco(db: Session, usuario: Usuario, espaco: Espaco) -> str | None:
    """O papel mais forte da pessoa no espaço (para mostrar na tela)."""
    papeis = papeis_no_espaco(db, usuario, espaco)
    return next((p for p in _FORCA if p in papeis), None)


def permissoes_no_espaco(papeis: set[str] | str | None) -> dict[str, bool]:
    if papeis is None:
        papeis = set()
    elif isinstance(papeis, str):
        papeis = {papeis}
    return {acao: bool(papeis & quem) for acao, quem in ACOES_ESPACO.items()}


def permissoes_do_usuario(db: Session, usuario: Usuario, espaco: Espaco) -> dict[str, bool]:
    return permissoes_no_espaco(papeis_no_espaco(db, usuario, espaco))


def pode_no_espaco(db: Session, usuario: Usuario, espaco: Espaco, acao: str) -> bool:
    return bool(papeis_no_espaco(db, usuario, espaco) & ACOES_ESPACO[acao])


def buscar_espaco(db: Session, usuario: Usuario, sigla: str, acao: str = "ver") -> Espaco:
    """Busca o espaço pela sigla e confere a permissão. Quem não vê o espaço recebe "não encontrado",
    para não revelar que um espaço privado existe."""
    espaco = db.scalar(select(Espaco).where(Espaco.sigla == sigla.upper()))
    if espaco is None or not pode_no_espaco(db, usuario, espaco, "ver"):
        raise NaoEncontrado("Espaço não encontrado.")
    if acao != "ver" and not pode_no_espaco(db, usuario, espaco, acao):
        raise SemPermissao("Você não tem permissão para esta ação.")
    return espaco


def _validar_sigla(db: Session, sigla: str) -> str:
    sigla = sigla.strip().upper()
    if not _SIGLA.match(sigla):
        raise OperacaoNegada("A sigla precisa ter de 2 a 10 letras, sem acentos, números ou espaços.")
    if db.scalar(select(Espaco.id).where(Espaco.sigla == sigla)) is not None:
        raise OperacaoNegada(f"A sigla {sigla} já é usada por outro espaço.")
    return sigla


def _validar_nome(nome: str, limite: int = 120) -> str:
    nome = nome.strip()
    if not nome:
        raise OperacaoNegada("Informe o nome.")
    if len(nome) > limite:
        raise OperacaoNegada(f"O nome pode ter até {limite} caracteres.")
    return nome


def criar_espaco(
    db: Session, ator: Usuario, tipo: str, nome: str, sigla: str, modelo: str | None, ip: str | None
) -> Espaco:
    if tipo == "projeto":
        exigir_plataforma(db, ator, "criar_espaco_equipe")
        if modelo not in MODELOS_PROJETO:
            raise OperacaoNegada("Escolha o modelo do espaço.")
    elif tipo == "pessoal":
        modelo = None
    else:
        raise OperacaoNegada("Tipo de espaço inválido.")
    espaco = Espaco(
        sigla=_validar_sigla(db, sigla),
        nome=_validar_nome(nome),
        tipo=tipo,
        modelo=modelo,
        dono_id=ator.id if tipo == "pessoal" else None,
        criado_por_id=ator.id,
        criado_em=relogio.agora(),
        proximo_numero=1,
    )
    db.add(espaco)
    db.flush()
    if tipo == "projeto":
        # Quem cria vira ADM do espaço (matriz: "Criar espaço de equipe (vira ADM dele)").
        db.add(MembroEspaco(espaco_id=espaco.id, usuario_id=ator.id, papel="adm", adicionado_por_id=ator.id,
                            adicionado_em=relogio.agora()))
    from .workflow import preparar_espaco

    preparar_espaco(db, espaco)
    registrar(db, TipoEvento.ESPACO_CRIADO, ator_id=ator.id, ip=ip, espaco=espaco.sigla, tipo_espaco=tipo, modelo=modelo)
    try:
        db.commit()
    except IntegrityError as erro:  # duas pessoas criando a mesma sigla ao mesmo tempo
        db.rollback()
        raise OperacaoNegada(f"A sigla {espaco.sigla} já é usada por outro espaço.") from erro
    return espaco


def editar_espaco(db: Session, ator: Usuario, espaco: Espaco, nome: str | None, descricao: str | None) -> None:
    if not pode_no_espaco(db, ator, espaco, "configurar"):
        raise SemPermissao("Você não tem permissão para esta ação.")
    if nome is not None:
        espaco.nome = _validar_nome(nome)
    if descricao is not None:
        espaco.descricao = descricao.strip() or None
    db.commit()


def listar_meus_espacos(db: Session, usuario: Usuario) -> list[tuple[Espaco, str]]:
    """Espaços do menu: onde a pessoa é membro (direto ou por time), os que acompanha como Gestor,
    os em suporte, os pessoais dela e os compartilhados com ela."""
    from .modelos_acesso import AcessoTime, Compartilhamento, GestorAcompanha, MembroTime, SessaoSuporte

    ids = set(db.scalars(select(MembroEspaco.espaco_id).where(MembroEspaco.usuario_id == usuario.id)))
    ids |= set(db.scalars(select(AcessoTime.espaco_id).join(MembroTime, MembroTime.time_id == AcessoTime.time_id)
                          .where(MembroTime.usuario_id == usuario.id)))
    ids |= set(db.scalars(select(GestorAcompanha.espaco_id).where(GestorAcompanha.usuario_id == usuario.id)))
    ids |= set(db.scalars(select(SessaoSuporte.espaco_id).where(
        SessaoSuporte.usuario_id == usuario.id, SessaoSuporte.encerrada_em.is_(None), SessaoSuporte.expira_em > relogio.agora())))
    ids |= set(db.scalars(select(Espaco.id).where(Espaco.tipo == "pessoal", Espaco.dono_id == usuario.id)))
    ids |= set(db.scalars(select(Compartilhamento.espaco_id).where(Compartilhamento.usuario_id == usuario.id)))
    resultado = []
    for espaco in db.scalars(select(Espaco).where(Espaco.id.in_(ids))) if ids else []:
        papel = papel_no_espaco(db, usuario, espaco)
        if papel:
            resultado.append((espaco, papel))
    return sorted(resultado, key=lambda par: (par[0].tipo != "projeto", par[0].nome.lower()))


def pessoas_com_papel(db: Session, espaco: Espaco, papeis: set[str]) -> set[uuid.UUID]:
    """Pessoas ativas com um destes papéis no espaço, diretamente ou por time."""
    from .modelos_acesso import AcessoTime, MembroTime

    diretos = set(db.scalars(select(MembroEspaco.usuario_id).join(Usuario, Usuario.id == MembroEspaco.usuario_id)
                             .where(MembroEspaco.espaco_id == espaco.id, MembroEspaco.papel.in_(papeis), Usuario.ativo)))
    por_time = set(db.scalars(
        select(MembroTime.usuario_id).join(AcessoTime, AcessoTime.time_id == MembroTime.time_id)
        .join(Usuario, Usuario.id == MembroTime.usuario_id)
        .where(AcessoTime.espaco_id == espaco.id, AcessoTime.papel.in_(papeis), Usuario.ativo)
    ))
    return diretos | por_time


# --- Membros ----------------------------------------------------------------------------------

def _contar_adms(db: Session, espaco: Espaco) -> int:
    """ADMs ativos do espaço, diretos ou por time."""
    return len(pessoas_com_papel(db, espaco, {"adm"}))


def _exigir_gerenciar_membros(db: Session, ator: Usuario, espaco: Espaco) -> None:
    if espaco.tipo == "pessoal":
        raise OperacaoNegada("Espaço pessoal não tem membros; ele pode ser compartilhado só para leitura.")
    if not pode_no_espaco(db, ator, espaco, "gerenciar_membros"):
        raise SemPermissao("Você não tem permissão para esta ação.")


def listar_membros(db: Session, espaco: Espaco) -> list[MembroEspaco]:
    return list(
        db.scalars(
            select(MembroEspaco).join(Usuario, Usuario.id == MembroEspaco.usuario_id)
            .where(MembroEspaco.espaco_id == espaco.id).order_by(Usuario.nome)
        ).unique()
    )


def adicionar_membro(
    db: Session, ator: Usuario, espaco: Espaco, usuario_id: uuid.UUID, papel: str, ip: str | None
) -> None:
    _exigir_gerenciar_membros(db, ator, espaco)
    if papel not in PAPEIS_ESPACO:
        raise OperacaoNegada("Papel inválido.")
    alvo = db.get(Usuario, usuario_id)
    if alvo is None:
        raise NaoEncontrado("Usuário não encontrado.")
    if not alvo.ativo:
        raise OperacaoNegada(f"{alvo.nome} está desativado.")
    existente = db.scalar(
        select(MembroEspaco).where(MembroEspaco.espaco_id == espaco.id, MembroEspaco.usuario_id == alvo.id)
    )
    if existente is not None:
        raise OperacaoNegada(f"{alvo.nome} já é {NOME_PAPEL_ESPACO[existente.papel]} deste espaço.")
    db.add(MembroEspaco(espaco_id=espaco.id, usuario_id=alvo.id, papel=papel, adicionado_por_id=ator.id,
                        adicionado_em=relogio.agora()))
    registrar(db, TipoEvento.MEMBRO_ADICIONADO, ator_id=ator.id, alvo_usuario_id=alvo.id, ip=ip,
              espaco=espaco.sigla, papel=papel)
    db.commit()


def _membro(db: Session, espaco: Espaco, usuario_id: uuid.UUID) -> MembroEspaco:
    membro = db.scalar(
        select(MembroEspaco).where(MembroEspaco.espaco_id == espaco.id, MembroEspaco.usuario_id == usuario_id)
    )
    if membro is None:
        raise NaoEncontrado("Essa pessoa não é membro deste espaço.")
    return membro


def mudar_papel_membro(
    db: Session, ator: Usuario, espaco: Espaco, usuario_id: uuid.UUID, papel: str, ip: str | None
) -> None:
    _exigir_gerenciar_membros(db, ator, espaco)
    if papel not in PAPEIS_ESPACO:
        raise OperacaoNegada("Papel inválido.")
    membro = _membro(db, espaco, usuario_id)
    if membro.papel == papel:
        return
    if membro.papel == "adm" and _contar_adms(db, espaco) <= 1:
        raise OperacaoNegada("O espaço precisa ter pelo menos um ADM.")
    anterior = membro.papel
    membro.papel = papel
    registrar(db, TipoEvento.MEMBRO_PAPEL_ALTERADO, ator_id=ator.id, alvo_usuario_id=usuario_id, ip=ip,
              espaco=espaco.sigla, de=anterior, para=papel)
    db.commit()


def remover_membro(db: Session, ator: Usuario, espaco: Espaco, usuario_id: uuid.UUID, ip: str | None) -> None:
    _exigir_gerenciar_membros(db, ator, espaco)
    membro = _membro(db, espaco, usuario_id)
    if membro.papel == "adm" and _contar_adms(db, espaco) <= 1:
        raise OperacaoNegada("O espaço precisa ter pelo menos um ADM.")
    papel = membro.papel
    db.delete(membro)
    registrar(db, TipoEvento.MEMBRO_REMOVIDO, ator_id=ator.id, alvo_usuario_id=usuario_id, ip=ip,
              espaco=espaco.sigla, papel=papel)
    db.commit()


# --- Painéis ----------------------------------------------------------------------------------

def listar_paineis(db: Session, espaco: Espaco) -> list[Painel]:
    return list(db.scalars(select(Painel).where(Painel.espaco_id == espaco.id).order_by(Painel.nome)))


def criar_painel(db: Session, ator: Usuario, espaco: Espaco, nome: str) -> Painel:
    if espaco.tipo == "pessoal":
        raise OperacaoNegada("Espaço pessoal não tem painéis.")
    if not pode_no_espaco(db, ator, espaco, "criar_paineis"):
        raise SemPermissao("Você não tem permissão para esta ação.")
    nome = _validar_nome(nome)
    if db.scalar(select(Painel.id).where(Painel.espaco_id == espaco.id, Painel.nome == nome)):
        raise OperacaoNegada(f"Já existe um painel chamado {nome}.")
    painel = Painel(espaco_id=espaco.id, nome=nome, criado_por_id=ator.id, criado_em=relogio.agora())
    db.add(painel)
    db.flush()
    from .workflow import preparar_painel

    preparar_painel(db, espaco, painel)
    db.commit()
    return painel


def _painel(db: Session, espaco: Espaco, painel_id: uuid.UUID) -> Painel:
    painel = db.get(Painel, painel_id)
    if painel is None or painel.espaco_id != espaco.id:
        raise NaoEncontrado("Painel não encontrado.")
    return painel


def renomear_painel(db: Session, ator: Usuario, espaco: Espaco, painel_id: uuid.UUID, nome: str) -> None:
    if not pode_no_espaco(db, ator, espaco, "criar_paineis"):
        raise SemPermissao("Você não tem permissão para esta ação.")
    painel = _painel(db, espaco, painel_id)
    nome = _validar_nome(nome)
    if db.scalar(select(Painel.id).where(Painel.espaco_id == espaco.id, Painel.nome == nome, Painel.id != painel.id)):
        raise OperacaoNegada(f"Já existe um painel chamado {nome}.")
    painel.nome = nome
    db.commit()


def excluir_painel(db: Session, ator: Usuario, espaco: Espaco, painel_id: uuid.UUID, em_uso: int) -> None:
    if not pode_no_espaco(db, ator, espaco, "criar_paineis"):
        raise SemPermissao("Você não tem permissão para esta ação.")
    painel = _painel(db, espaco, painel_id)
    if em_uso:
        raise OperacaoNegada(f"O painel {painel.nome} tem {em_uso} item(ns). Mova os itens antes de excluir.")
    db.delete(painel)
    db.commit()


# --- Tipos de item ----------------------------------------------------------------------------

def listar_tipos(db: Session, espaco: Espaco) -> list[TipoItem]:
    return list(
        db.scalars(
            select(TipoItem)
            .where((TipoItem.espaco_id.is_(None)) | (TipoItem.espaco_id == espaco.id))
            .order_by(TipoItem.ordem, TipoItem.nome)
        )
    )


def criar_tipo(db: Session, ator: Usuario, espaco: Espaco, nome: str) -> TipoItem:
    """Tipos próprios ficam no nível de História, Tarefa e Bug (decisão de 16/11)."""
    if not pode_no_espaco(db, ator, espaco, "configurar"):
        raise SemPermissao("Você não tem permissão para esta ação.")
    nome = _validar_nome(nome, 60)
    existentes = {t.nome.lower() for t in listar_tipos(db, espaco)}
    if nome.lower() in existentes:
        raise OperacaoNegada(f"Já existe um tipo chamado {nome}.")
    tipo = TipoItem(espaco_id=espaco.id, nome=nome, nivel="padrao", ordem=50)
    db.add(tipo)
    db.commit()
    return tipo


def _tipo_proprio(db: Session, espaco: Espaco, tipo_id: uuid.UUID) -> TipoItem:
    tipo = db.get(TipoItem, tipo_id)
    if tipo is None or (tipo.espaco_id is not None and tipo.espaco_id != espaco.id):
        raise NaoEncontrado("Tipo não encontrado.")
    if tipo.espaco_id is None:
        raise OperacaoNegada("Os tipos padrão da plataforma não podem ser alterados.")
    return tipo


def renomear_tipo(db: Session, ator: Usuario, espaco: Espaco, tipo_id: uuid.UUID, nome: str) -> None:
    if not pode_no_espaco(db, ator, espaco, "configurar"):
        raise SemPermissao("Você não tem permissão para esta ação.")
    tipo = _tipo_proprio(db, espaco, tipo_id)
    nome = _validar_nome(nome, 60)
    if nome.lower() in {t.nome.lower() for t in listar_tipos(db, espaco) if t.id != tipo.id}:
        raise OperacaoNegada(f"Já existe um tipo chamado {nome}.")
    tipo.nome = nome
    db.commit()


def excluir_tipo(db: Session, ator: Usuario, espaco: Espaco, tipo_id: uuid.UUID, em_uso: int) -> None:
    if not pode_no_espaco(db, ator, espaco, "configurar"):
        raise SemPermissao("Você não tem permissão para esta ação.")
    tipo = _tipo_proprio(db, espaco, tipo_id)
    if em_uso:
        raise OperacaoNegada(f"Há {em_uso} item(ns) do tipo {tipo.nome}. Mude o tipo deles antes de excluir.")
    db.delete(tipo)
    db.commit()


def listar_status(db: Session, espaco: Espaco) -> list[StatusItem]:
    """Status ligados no espaço, na ordem do espaço (Etapa 3a)."""
    from .workflow import status_do_espaco

    return status_do_espaco(db, espaco)


# --- Origens da solicitação -------------------------------------------------------------------

def listar_origens(db: Session, espaco: Espaco, incluir_inativas: bool = False) -> list[OpcaoOrigem]:
    consulta = select(OpcaoOrigem).where(OpcaoOrigem.espaco_id == espaco.id).order_by(OpcaoOrigem.nome)
    if not incluir_inativas:
        consulta = consulta.where(OpcaoOrigem.ativo)
    return list(db.scalars(consulta))


def criar_origem(db: Session, ator: Usuario, espaco: Espaco, nome: str) -> OpcaoOrigem:
    if not pode_no_espaco(db, ator, espaco, "configurar"):
        raise SemPermissao("Você não tem permissão para esta ação.")
    nome = _validar_nome(nome)
    existente = db.scalar(select(OpcaoOrigem).where(OpcaoOrigem.espaco_id == espaco.id, OpcaoOrigem.nome == nome))
    if existente is not None:
        if existente.ativo:
            raise OperacaoNegada(f"A origem {nome} já existe.")
        existente.ativo = True
        db.commit()
        return existente
    origem = OpcaoOrigem(espaco_id=espaco.id, nome=nome, ativo=True)
    db.add(origem)
    db.commit()
    return origem


def desativar_origem(db: Session, ator: Usuario, espaco: Espaco, origem_id: uuid.UUID) -> None:
    """A origem sai da lista de escolha, mas continua nos itens que já a usam."""
    if not pode_no_espaco(db, ator, espaco, "configurar"):
        raise SemPermissao("Você não tem permissão para esta ação.")
    origem = db.get(OpcaoOrigem, origem_id)
    if origem is None or origem.espaco_id != espaco.id:
        raise NaoEncontrado("Origem não encontrada.")
    origem.ativo = False
    db.commit()
