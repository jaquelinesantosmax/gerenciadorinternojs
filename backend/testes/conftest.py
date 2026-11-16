"""Preparação dos testes. Usam o banco gerenciador_teste, recriado do zero a cada rodada.

Antes de rodar: infra\\ligar-banco.ps1 (liga o banco). Depois: .venv\\Scripts\\python -m pytest
"""

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def _ler_env() -> dict[str, str]:
    arquivo = RAIZ / "infra" / ".env"
    if not arquivo.exists():
        raise RuntimeError("Configuração local não encontrada. Rode infra\\ligar-banco.ps1 antes dos testes.")
    cfg = {}
    for linha in arquivo.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" in linha and not linha.lstrip().startswith("#"):
            chave, valor = linha.split("=", 1)
            cfg[chave.strip()] = valor.strip()
    return cfg


_cfg = _ler_env()
os.environ["GERENCIADOR_DATABASE_URL"] = (
    f"postgresql+psycopg://{_cfg['PG_USUARIO']}:{_cfg['PG_SENHA']}@localhost:{_cfg['PG_PORTA']}/gerenciador_teste"
)
os.environ["GERENCIADOR_LOGIN_TESTE_HABILITADO"] = "true"
os.environ["GERENCIADOR_AMBIENTE"] = "desenvolvimento"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config as ConfigAlembic  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from gerenciador import relogio  # noqa: E402
from gerenciador.banco import nova_sessao, obter_engine  # noqa: E402
from gerenciador.papeis import cadastrar_adm_instalacao  # noqa: E402
from gerenciador.principal import criar_app  # noqa: E402

TABELAS = [
    "eventos_auditoria", "sessoes", "concessoes_papel", "dominios_autorizados", "usuarios", "times", "espacos",
    "membros_espaco", "paineis", "tipos_item", "status_item", "opcoes_origem", "itens", "co_responsaveis",
    "apelidos_item", "campos_personalizados", "historico_item", "comentarios", "versoes_comentario", "anexos",
    "vinculos", "config_plataforma",
]

# Mesmos dados iniciais das migrações (tipos e status padrão, limite de anexos).
SEMENTES = [
    "INSERT INTO dominios_autorizados (dominio, adicionado_em) VALUES "
    "('jusbrasil.com.br', now()), ('digesto.com.br', now())",
    "INSERT INTO tipos_item (id, espaco_id, nome, nivel, ordem) VALUES "
    "(gen_random_uuid(), NULL, 'Épico', 'epico', 10), (gen_random_uuid(), NULL, 'História', 'padrao', 20), "
    "(gen_random_uuid(), NULL, 'Tarefa', 'padrao', 30), (gen_random_uuid(), NULL, 'Bug', 'padrao', 40), "
    "(gen_random_uuid(), NULL, 'Subtarefa', 'subtarefa', 90)",
    "INSERT INTO status_item (id, espaco_id, nome, categoria, ordem) VALUES "
    "(gen_random_uuid(), NULL, 'Backlog', 'a_fazer', 10), (gen_random_uuid(), NULL, 'A fazer', 'a_fazer', 20), "
    "(gen_random_uuid(), NULL, 'Em andamento', 'em_andamento', 30), "
    "(gen_random_uuid(), NULL, 'Em validação', 'em_andamento', 40), "
    "(gen_random_uuid(), NULL, 'Aguardando terceiros', 'em_andamento', 50), "
    "(gen_random_uuid(), NULL, 'Bloqueado', 'em_andamento', 60), "
    "(gen_random_uuid(), NULL, 'Concluído', 'concluido', 70), (gen_random_uuid(), NULL, 'Cancelado', 'concluido', 80)",
    "INSERT INTO config_plataforma (chave, valor) VALUES ('limite_anexo_mb', '1024'::jsonb)",
]


@pytest.fixture(scope="session", autouse=True)
def esquema():
    """Recria o banco de teste aplicando as migrações reais, para testar as migrações também."""
    with obter_engine().begin() as conexao:
        conexao.execute(text("DROP SCHEMA public CASCADE"))
        conexao.execute(text("CREATE SCHEMA public"))
    cfg = ConfigAlembic(str(RAIZ / "backend" / "alembic.ini"))
    cfg.set_main_option("script_location", str(RAIZ / "backend" / "migracoes"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def limpar():
    with obter_engine().begin() as conexao:
        conexao.execute(text(f"TRUNCATE {', '.join(TABELAS)} RESTART IDENTITY CASCADE"))
        for sql in SEMENTES:
            conexao.execute(text(sql))
    yield


@pytest.fixture
def db():
    sessao = nova_sessao()
    yield sessao
    sessao.close()


@pytest.fixture
def app():
    return criar_app()


@pytest.fixture
def novo_cliente(app):
    """Cria navegadores independentes (cada um com seus próprios cookies)."""
    abertos = []

    def criar() -> TestClient:
        cliente = TestClient(app, headers={"X-Gerenciador": "1"})
        abertos.append(cliente)
        return cliente

    yield criar
    for cliente in abertos:
        cliente.close()


@pytest.fixture
def cliente(novo_cliente):
    return novo_cliente()


def entrar(cliente: TestClient, email: str, nome: str = "Pessoa Teste") -> dict:
    resposta = cliente.post("/api/auth/teste/entrar", json={"email": email, "nome": nome})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


@pytest.fixture
def adm(db):
    """ADM da plataforma cadastrado como na instalação."""
    return cadastrar_adm_instalacao(db, "ana.adm@jusbrasil.com.br", "Ana Adm")


@pytest.fixture
def cliente_adm(novo_cliente, adm):
    c = novo_cliente()
    entrar(c, adm.email)
    return c


class RelogioFalso:
    def __init__(self):
        self.atual = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)

    def avancar(self, **intervalo) -> None:
        self.atual += timedelta(**intervalo)


@pytest.fixture
def relogio_falso(monkeypatch):
    falso = RelogioFalso()
    monkeypatch.setattr(relogio, "agora", lambda: falso.atual)
    return falso


def eventos(db, tipo: str | None = None) -> list:
    from sqlalchemy import select

    from gerenciador.modelos import EventoAuditoria

    consulta = select(EventoAuditoria).order_by(EventoAuditoria.id)
    if tipo:
        consulta = consulta.where(EventoAuditoria.tipo == tipo)
    db.expire_all()
    return list(db.scalars(consulta).unique())


def _id(cliente) -> str:
    return cliente.get("/api/eu").json()["id"]


def criar_projeto(cliente, sigla="LOP", nome="Legal Ops", modelo="kanban"):
    resposta = cliente.post("/api/espacos", json={"tipo": "projeto", "nome": nome, "sigla": sigla, "modelo": modelo})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


@pytest.fixture
def cenario(novo_cliente, cliente_adm):
    """Espaço LOP com um time, um Membro e um Leitor. Devolve um dicionário com tudo que os testes usam."""
    espaco = criar_projeto(cliente_adm)
    time = cliente_adm.post("/api/admin/times", json={"nome": "Legal Ops"}).json()
    membro, leitor = novo_cliente(), novo_cliente()
    entrar(membro, "membro@jusbrasil.com.br", "Marta Membro")
    entrar(leitor, "leitor@jusbrasil.com.br", "Leo Leitor")
    cliente_adm.post("/api/espacos/LOP/membros", json={"usuario_id": _id(membro), "papel": "membro"})
    cliente_adm.post("/api/espacos/LOP/membros", json={"usuario_id": _id(leitor), "papel": "leitor"})
    tipos = {t["nome"]: t["id"] for t in espaco["tipos"]}
    status = {s["nome"]: s["id"] for s in espaco["status"]}
    return {"adm": cliente_adm, "membro": membro, "leitor": leitor, "tipos": tipos, "status": status,
            "time": time["id"], "membro_id": _id(membro), "adm_id": _id(cliente_adm), "leitor_id": _id(leitor)}


def dados_item(c, **extra):
    base = {
        "tipo_id": c["tipos"]["Tarefa"], "resumo": "Revisar fluxo de prazos", "status_id": c["status"]["A fazer"],
        "prioridade": "alta", "responsavel_id": c["membro_id"], "time_id": c["time"],
        "data_inicio": "2026-11-16", "data_entrega": "2026-11-30",
    }
    base.update(extra)
    return base


def criar_item(cliente, c, sigla="LOP", **extra):
    r = cliente.post(f"/api/espacos/{sigla}/itens", json={"dados": dados_item(c, **extra)})
    assert r.status_code == 201, r.text
    return r.json()
