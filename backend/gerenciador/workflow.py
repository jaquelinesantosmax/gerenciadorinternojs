"""Status, workflow e quadros (Etapa 3a).

- Status padrão são mantidos pelo ADM da plataforma; status próprios são criados pelo ADM do espaço
  e só existem naquele espaço. Todo status tem categoria (A fazer, Em andamento ou Concluído).
- Todo espaço nasce com os 8 status padrão ligados e com o fluxo padrão (decisões de 16/11).
- Nome parecido com um status existente gera aviso antes de salvar.
- Status em uso só é desligado ou apagado depois de mover os itens.
- O quadro nasce com uma coluna por status; no Kanban, Backlog fica numa área separada.
"""

import unicodedata
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import relogio
from .erros import ErroDeRegra, NaoEncontrado, OperacaoNegada, SemPermissao
from .modelos import Usuario
from .modelos_espacos import CATEGORIAS_STATUS, Espaco, Painel, StatusItem
from .modelos_itens import Item
from .modelos_quadros import TIPOS_QUADRO, ColunaQuadro, Quadro, StatusDoEspaco, Transicao

# Fluxo padrão aprovado em 16/11, igual nos três modelos.
FLUXO_PADRAO = [
    ("Backlog", "A fazer"),
    ("A fazer", "Em andamento"),
    ("Em andamento", "Em validação"),
    ("Em validação", "Concluído"),
    ("Em andamento", "Aguardando terceiros"),
    ("Aguardando terceiros", "Em andamento"),
    ("Em andamento", "Bloqueado"),
    ("Bloqueado", "Em andamento"),
    ("Em validação", "Em andamento"),
    ("Concluído", "A fazer"),
    ("Cancelado", "A fazer"),
] + [(s, "Cancelado") for s in ("Backlog", "A fazer", "Em andamento", "Em validação", "Aguardando terceiros",
                                  "Bloqueado", "Concluído")]

NOME_BACKLOG = "Backlog"
NOMES_CATEGORIA = {"a_fazer": "A fazer", "em_andamento": "Em andamento", "concluido": "Concluído"}
TIPO_QUADRO_DO_MODELO = {"kanban": "kanban", "gestao_tarefas": "simples", "scrum": "scrum", None: "simples"}

# Nomes em inglês que costumam duplicar status em português (ex.: "BLOCKED" e "Bloqueado" no TLF).
_SINONIMOS = {
    "blocked": "bloqueado", "done": "concluido", "to do": "a fazer", "todo": "a fazer", "in progress": "em andamento",
    "doing": "em andamento", "review": "em validacao", "in review": "em validacao", "canceled": "cancelado",
    "cancelled": "cancelado", "waiting": "aguardando terceiros", "on hold": "aguardando terceiros",
    "backlog": "backlog", "validacao": "em validacao", "concluida": "concluido", "feito": "concluido",
}


class AvisoNomeParecido(OperacaoNegada):
    def __init__(self, parecido: str):
        super().__init__(f"Já existe o status \"{parecido}\", com nome parecido. Criar mesmo assim?")
        self.parecido = parecido


def _normalizar(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFD", nome).encode("ascii", "ignore").decode()
    simples = " ".join(sem_acento.lower().replace("-", " ").replace("_", " ").split())
    return _SINONIMOS.get(simples, simples)


def _distancia(a: str, b: str) -> int:
    anterior = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        atual = [i]
        for j, cb in enumerate(b, 1):
            atual.append(min(anterior[j] + 1, atual[j - 1] + 1, anterior[j - 1] + (ca != cb)))
        anterior = atual
    return anterior[-1]


def nome_parecido(nome: str, existentes: list[str]) -> str | None:
    alvo = _normalizar(nome)
    for existente in existentes:
        outro = _normalizar(existente)
        if alvo == outro or (min(len(alvo), len(outro)) >= 5 and _distancia(alvo, outro) <= 2):
            return existente
    return None


# --- Consultas --------------------------------------------------------------------------------

def status_do_espaco(db: Session, espaco: Espaco) -> list[StatusItem]:
    return list(
        db.scalars(
            select(StatusItem).join(StatusDoEspaco, StatusDoEspaco.status_id == StatusItem.id)
            .where(StatusDoEspaco.espaco_id == espaco.id).order_by(StatusDoEspaco.ordem)
        )
    )


def transicoes(db: Session, espaco: Espaco) -> set[tuple[uuid.UUID, uuid.UUID]]:
    linhas = db.execute(select(Transicao.de_status_id, Transicao.para_status_id).where(Transicao.espaco_id == espaco.id))
    return {(de, para) for de, para in linhas}


def destinos(db: Session, espaco: Espaco, de: uuid.UUID) -> list[uuid.UUID]:
    return [para for (origem, para) in transicoes(db, espaco) if origem == de]


def conferir_transicao(db: Session, espaco: Espaco, de: StatusItem, para: StatusItem) -> None:
    if de.id == para.id:
        return
    if (de.id, para.id) not in transicoes(db, espaco):
        permitidos = set(destinos(db, espaco, de.id))
        possiveis = [s.nome for s in status_do_espaco(db, espaco) if s.id in permitidos]
        caminho = ", ".join(possiveis) if possiveis else "nenhum (fale com o ADM do espaço)"
        raise ErroDeRegra(f"O fluxo não permite ir de {de.nome} para {para.nome}. De {de.nome}, o item pode ir para: {caminho}.")


def itens_no_status(db: Session, espaco: Espaco, status_id: uuid.UUID) -> int:
    return db.scalar(select(func.count()).select_from(Item).where(
        Item.espaco_id == espaco.id, Item.status_id == status_id, Item.excluido_em.is_(None))) or 0


# --- Preparação de espaços e painéis ----------------------------------------------------------

def _colunas_padrao(db: Session, espaco: Espaco, usa_backlog: bool) -> list[ColunaQuadro]:
    colunas = []
    for status in status_do_espaco(db, espaco):
        if usa_backlog and status.nome == NOME_BACKLOG and status.espaco_id is None:
            continue
        colunas.append(ColunaQuadro(nome=status.nome, ordem=len(colunas), limite=None, status_ids=[status.id]))
    return colunas


def criar_quadro(
    db: Session, espaco: Espaco, nome: str, tipo: str, painel: Painel | None = None, modelo_colunas: Quadro | None = None
) -> Quadro:
    if tipo not in TIPOS_QUADRO:
        raise ErroDeRegra("Tipo de quadro inválido.")
    usa_backlog = tipo in ("kanban", "scrum")
    quadro = Quadro(espaco_id=espaco.id, painel_id=painel.id if painel else None, nome=nome, tipo=tipo,
                    usa_backlog=modelo_colunas.usa_backlog if modelo_colunas else usa_backlog, criado_em=relogio.agora())
    db.add(quadro)
    db.flush()
    if modelo_colunas is not None:
        for c in colunas_do_quadro(db, modelo_colunas):
            db.add(ColunaQuadro(quadro_id=quadro.id, nome=c.nome, ordem=c.ordem, limite=c.limite, status_ids=list(c.status_ids)))
    else:
        for c in _colunas_padrao(db, espaco, quadro.usa_backlog):
            c.quadro_id = quadro.id
            db.add(c)
    return quadro


def quadro_principal(db: Session, espaco: Espaco) -> Quadro | None:
    return db.scalar(select(Quadro).where(Quadro.espaco_id == espaco.id, Quadro.painel_id.is_(None))
                     .order_by(Quadro.criado_em))


def preparar_espaco(db: Session, espaco: Espaco) -> None:
    """Liga os 8 status padrão, cria o fluxo padrão e o quadro do modelo. Não faz commit."""
    padrao = list(db.scalars(select(StatusItem).where(StatusItem.espaco_id.is_(None)).order_by(StatusItem.ordem)))
    for ordem, status in enumerate(s for s in padrao if s.nome in {n for par in FLUXO_PADRAO for n in par}):
        db.add(StatusDoEspaco(espaco_id=espaco.id, status_id=status.id, ordem=ordem))
    por_nome = {s.nome: s.id for s in padrao}
    for de, para in FLUXO_PADRAO:
        if de in por_nome and para in por_nome:
            db.add(Transicao(espaco_id=espaco.id, de_status_id=por_nome[de], para_status_id=por_nome[para]))
    db.flush()
    criar_quadro(db, espaco, "Quadro", TIPO_QUADRO_DO_MODELO.get(espaco.modelo, "simples"))


def preparar_painel(db: Session, espaco: Espaco, painel: Painel) -> None:
    """Cada painel tem quadro e colunas próprios; nasce com as colunas do quadro principal do espaço."""
    criar_quadro(db, espaco, painel.nome, TIPO_QUADRO_DO_MODELO.get(espaco.modelo, "simples"), painel=painel,
                 modelo_colunas=quadro_principal(db, espaco))


# --- Status no espaço (ADM do espaço) ---------------------------------------------------------

def _exigir_configurar(db: Session, ator: Usuario, espaco: Espaco) -> None:
    from .espacos import pode_no_espaco

    if not pode_no_espaco(db, ator, espaco, "configurar"):
        raise SemPermissao("Você não tem permissão para esta ação.")


def _categoria(categoria: str) -> str:
    if categoria not in CATEGORIAS_STATUS:
        raise ErroDeRegra("Escolha a categoria do status: A fazer, Em andamento ou Concluído.")
    return categoria


def _nome_status(nome: str) -> str:
    nome = nome.strip()
    if not nome:
        raise ErroDeRegra("Informe o nome do status.")
    if len(nome) > 60:
        raise ErroDeRegra("O nome pode ter até 60 caracteres.")
    return nome


def _ligar(db: Session, espaco: Espaco, status: StatusItem) -> None:
    ordem = (db.scalar(select(func.max(StatusDoEspaco.ordem)).where(StatusDoEspaco.espaco_id == espaco.id)) or 0) + 1
    db.add(StatusDoEspaco(espaco_id=espaco.id, status_id=status.id, ordem=ordem))
    # O status novo ganha uma coluna no fim de cada quadro do espaço; o ADM junta colunas depois, se quiser.
    for quadro in db.scalars(select(Quadro).where(Quadro.espaco_id == espaco.id)):
        if quadro.usa_backlog and status.nome == NOME_BACKLOG and status.espaco_id is None:
            continue
        ultima = db.scalar(select(func.max(ColunaQuadro.ordem)).where(ColunaQuadro.quadro_id == quadro.id))
        db.add(ColunaQuadro(quadro_id=quadro.id, nome=status.nome, ordem=(ultima or 0) + 1, limite=None,
                            status_ids=[status.id]))


def criar_status(db: Session, ator: Usuario, espaco: Espaco, nome: str, categoria: str, confirmar: bool) -> StatusItem:
    """Status próprio: só existe neste espaço."""
    _exigir_configurar(db, ator, espaco)
    nome = _nome_status(nome)
    visiveis = status_do_espaco(db, espaco) + list(db.scalars(select(StatusItem).where(StatusItem.espaco_id.is_(None))))
    if any(s.nome.lower() == nome.lower() for s in visiveis):
        raise OperacaoNegada(f"Já existe o status {nome}. Se for um status padrão, ligue-o na lista de disponíveis.")
    parecido = nome_parecido(nome, [s.nome for s in visiveis])
    if parecido and not confirmar:
        raise AvisoNomeParecido(parecido)
    status = StatusItem(espaco_id=espaco.id, nome=nome, categoria=_categoria(categoria), ordem=1000)
    db.add(status)
    db.flush()
    _ligar(db, espaco, status)
    db.commit()
    return status


def _status(db: Session, status_id: uuid.UUID) -> StatusItem:
    status = db.get(StatusItem, status_id)
    if status is None:
        raise NaoEncontrado("Status não encontrado.")
    return status


def ligar_status(db: Session, ator: Usuario, espaco: Espaco, status_id: uuid.UUID) -> None:
    """Liga um status padrão (ou promovido) que estava fora do espaço."""
    _exigir_configurar(db, ator, espaco)
    status = _status(db, status_id)
    if status.espaco_id not in (None, espaco.id):
        raise NaoEncontrado("Status não encontrado.")
    if status.id in {s.id for s in status_do_espaco(db, espaco)}:
        raise OperacaoNegada(f"O status {status.nome} já está ligado.")
    _ligar(db, espaco, status)
    db.commit()


def desligar_status(db: Session, ator: Usuario, espaco: Espaco, status_id: uuid.UUID) -> None:
    """Tira o status do espaço. Status próprio desligado é apagado. Só funciona sem itens nele."""
    _exigir_configurar(db, ator, espaco)
    status = _status(db, status_id)
    ligados = status_do_espaco(db, espaco)
    if status.id not in {s.id for s in ligados}:
        raise NaoEncontrado("Status não encontrado.")
    em_uso = itens_no_status(db, espaco, status.id)
    if em_uso:
        raise OperacaoNegada(f"Há {em_uso} item(ns) em {status.nome}. Mova os itens para outro status antes.")
    if len(ligados) <= 1:
        raise OperacaoNegada("O espaço precisa de pelo menos um status.")
    db.execute(delete(StatusDoEspaco).where(StatusDoEspaco.espaco_id == espaco.id, StatusDoEspaco.status_id == status.id))
    db.execute(delete(Transicao).where(Transicao.espaco_id == espaco.id,
                                       (Transicao.de_status_id == status.id) | (Transicao.para_status_id == status.id)))
    for quadro in db.scalars(select(Quadro).where(Quadro.espaco_id == espaco.id)):
        for coluna in colunas_do_quadro(db, quadro):
            if status.id in coluna.status_ids:
                restantes = [s for s in coluna.status_ids if s != status.id]
                if restantes:
                    coluna.status_ids = restantes
                else:
                    db.delete(coluna)
    if status.espaco_id == espaco.id:
        db.flush()
        db.delete(status)
    db.commit()


def renomear_status(db: Session, ator: Usuario, espaco: Espaco, status_id: uuid.UUID, nome: str, confirmar: bool) -> None:
    _exigir_configurar(db, ator, espaco)
    status = _status(db, status_id)
    if status.espaco_id != espaco.id:
        raise OperacaoNegada("Status padrão só é alterado pelo ADM da plataforma.")
    nome = _nome_status(nome)
    outros = [s.nome for s in status_do_espaco(db, espaco) if s.id != status.id]
    if any(n.lower() == nome.lower() for n in outros):
        raise OperacaoNegada(f"Já existe o status {nome}.")
    parecido = nome_parecido(nome, outros)
    if parecido and not confirmar:
        raise AvisoNomeParecido(parecido)
    status.nome = nome
    db.commit()


def definir_transicoes(db: Session, ator: Usuario, espaco: Espaco, pares: list[tuple[uuid.UUID, uuid.UUID]]) -> None:
    _exigir_configurar(db, ator, espaco)
    ligados = {s.id for s in status_do_espaco(db, espaco)}
    limpos = set()
    for de, para in pares:
        if de not in ligados or para not in ligados:
            raise ErroDeRegra("Transição com status que não está ligado no espaço.")
        if de != para:
            limpos.add((de, para))
    db.execute(delete(Transicao).where(Transicao.espaco_id == espaco.id))
    for de, para in limpos:
        db.add(Transicao(espaco_id=espaco.id, de_status_id=de, para_status_id=para))
    db.commit()


# --- Catálogo padrão (ADM da plataforma) ------------------------------------------------------

def status_padrao(db: Session) -> list[StatusItem]:
    return list(db.scalars(select(StatusItem).where(StatusItem.espaco_id.is_(None)).order_by(StatusItem.ordem, StatusItem.nome)))


def criar_status_padrao(db: Session, ator: Usuario, nome: str, categoria: str, confirmar: bool) -> StatusItem:
    from .papeis import exigir

    exigir(db, ator, "gerenciar_status_padrao")
    nome = _nome_status(nome)
    existentes = [s.nome for s in status_padrao(db)]
    if any(n.lower() == nome.lower() for n in existentes):
        raise OperacaoNegada(f"Já existe o status padrão {nome}.")
    parecido = nome_parecido(nome, existentes)
    if parecido and not confirmar:
        raise AvisoNomeParecido(parecido)
    ordem = (db.scalar(select(func.max(StatusItem.ordem)).where(StatusItem.espaco_id.is_(None))) or 0) + 10
    status = StatusItem(espaco_id=None, nome=nome, categoria=_categoria(categoria), ordem=ordem)
    db.add(status)
    db.commit()
    return status


def promover_status(db: Session, ator: Usuario, status_id: uuid.UUID) -> None:
    """Status de um espaço passa a ser padrão: fica disponível como opção nos outros espaços, sem ser imposto."""
    from .papeis import exigir

    exigir(db, ator, "gerenciar_status_padrao")
    status = _status(db, status_id)
    if status.espaco_id is None:
        raise OperacaoNegada(f"{status.nome} já é um status padrão.")
    if any(s.nome.lower() == status.nome.lower() for s in status_padrao(db)):
        raise OperacaoNegada(f"Já existe o status padrão {status.nome}.")
    status.espaco_id = None
    status.ordem = (db.scalar(select(func.max(StatusItem.ordem)).where(StatusItem.espaco_id.is_(None))) or 0) + 10
    db.commit()


def status_proprios_de_todos(db: Session) -> list[tuple[StatusItem, Espaco]]:
    return list(db.execute(select(StatusItem, Espaco).join(Espaco, Espaco.id == StatusItem.espaco_id)
                           .order_by(Espaco.sigla, StatusItem.nome)).all())


# --- Quadros ----------------------------------------------------------------------------------

def colunas_do_quadro(db: Session, quadro: Quadro) -> list[ColunaQuadro]:
    return list(db.scalars(select(ColunaQuadro).where(ColunaQuadro.quadro_id == quadro.id).order_by(ColunaQuadro.ordem)))


def quadros_do_espaco(db: Session, espaco: Espaco) -> list[Quadro]:
    return list(db.scalars(select(Quadro).where(Quadro.espaco_id == espaco.id).order_by(Quadro.criado_em)))


def buscar_quadro(db: Session, quadro_id: uuid.UUID) -> Quadro:
    quadro = db.get(Quadro, quadro_id)
    if quadro is None:
        raise NaoEncontrado("Quadro não encontrado.")
    return quadro


def novo_quadro(db: Session, ator: Usuario, espaco: Espaco, nome: str, tipo: str) -> Quadro:
    _exigir_configurar(db, ator, espaco)
    nome = nome.strip()
    if not nome:
        raise ErroDeRegra("Informe o nome do quadro.")
    quadro = criar_quadro(db, espaco, nome[:120], tipo)
    db.commit()
    return quadro


def excluir_quadro(db: Session, ator: Usuario, espaco: Espaco, quadro: Quadro) -> None:
    _exigir_configurar(db, ator, espaco)
    if quadro.painel_id is not None:
        raise OperacaoNegada("O quadro de um painel sai junto com o painel.")
    if len([q for q in quadros_do_espaco(db, espaco) if q.painel_id is None]) <= 1:
        raise OperacaoNegada("O espaço precisa de pelo menos um quadro.")
    db.delete(quadro)
    db.commit()


def alterar_quadro(db: Session, ator: Usuario, espaco: Espaco, quadro: Quadro, nome: str | None, usa_backlog: bool | None) -> None:
    _exigir_configurar(db, ator, espaco)
    if nome is not None and nome.strip():
        quadro.nome = nome.strip()[:120]
    if usa_backlog is not None and usa_backlog != quadro.usa_backlog:
        if quadro.tipo == "simples" and usa_backlog:
            raise OperacaoNegada("O quadro simples não tem área de backlog.")
        backlog = next((s for s in status_do_espaco(db, espaco) if s.nome == NOME_BACKLOG and s.espaco_id is None), None)
        colunas = colunas_do_quadro(db, quadro)
        if backlog is not None:
            if usa_backlog:
                for c in colunas:
                    if backlog.id in c.status_ids:
                        restantes = [s for s in c.status_ids if s != backlog.id]
                        if restantes:
                            c.status_ids = restantes
                        else:
                            db.delete(c)
            elif not any(backlog.id in c.status_ids for c in colunas):
                # Desligar o backlog: Backlog vira a primeira coluna (decisão de 16/11).
                for c in colunas:
                    c.ordem += 1
                db.add(ColunaQuadro(quadro_id=quadro.id, nome=NOME_BACKLOG, ordem=0, limite=None, status_ids=[backlog.id]))
        quadro.usa_backlog = usa_backlog
    db.commit()


def definir_colunas(db: Session, ator: Usuario, espaco: Espaco, quadro: Quadro, colunas: list[dict]) -> None:
    """Troca as colunas do quadro. Cada status fica em no máximo uma coluna."""
    _exigir_configurar(db, ator, espaco)
    ligados = {s.id: s for s in status_do_espaco(db, espaco)}
    vistos: set[uuid.UUID] = set()
    novas = []
    for ordem, c in enumerate(colunas):
        nome = str(c.get("nome") or "").strip()
        if not nome:
            raise ErroDeRegra("Toda coluna precisa de um nome.")
        status_ids = [uuid.UUID(str(s)) for s in c.get("status_ids") or []]
        if not status_ids:
            raise ErroDeRegra(f"A coluna {nome} precisa de pelo menos um status.")
        for s in status_ids:
            if s not in ligados:
                raise ErroDeRegra("Coluna com status que não está ligado no espaço.")
            if s in vistos:
                raise ErroDeRegra(f"O status {ligados[s].nome} está em mais de uma coluna.")
            vistos.add(s)
        limite = c.get("limite")
        if limite in ("", None):
            limite = None
        else:
            limite = int(limite)
            if limite < 1:
                raise ErroDeRegra(f"O limite da coluna {nome} precisa ser maior que zero.")
        novas.append(ColunaQuadro(quadro_id=quadro.id, nome=nome[:80], ordem=ordem, limite=limite, status_ids=status_ids))
    if not novas:
        raise ErroDeRegra("O quadro precisa de pelo menos uma coluna.")
    db.execute(delete(ColunaQuadro).where(ColunaQuadro.quadro_id == quadro.id))
    for c in novas:
        db.add(c)
    db.commit()


def nome_categoria(categoria: str) -> str:
    return NOMES_CATEGORIA.get(categoria, categoria)
