"""Login, cadastro automático no primeiro acesso e domínios autorizados."""

import pytest
from conftest import entrar, eventos
from sqlalchemy import func, select

from gerenciador.config import Config, obter_config
from gerenciador.modelos import Usuario


def test_primeiro_login_cadastra_sem_nenhum_papel(cliente, db):
    eu = entrar(cliente, "maria.silva@jusbrasil.com.br", "Maria Silva")

    assert eu["email"] == "maria.silva@jusbrasil.com.br"
    assert eu["nome"] == "Maria Silva"
    assert eu["papeis"] == []
    assert not any(eu["permissoes"].values())
    assert [e.tipo for e in eventos(db)] == ["cadastro_automatico", "login"]


def test_email_e_normalizado_e_segundo_login_nao_duplica(novo_cliente, db):
    entrar(novo_cliente(), "  Maria.Silva@JUSBRASIL.com.br ", "Maria Silva")
    entrar(novo_cliente(), "maria.silva@jusbrasil.com.br", "Outro Nome")

    assert db.scalar(select(func.count()).select_from(Usuario)) == 1
    usuario = db.scalar(select(Usuario))
    assert usuario.email == "maria.silva@jusbrasil.com.br"
    # O login de teste não altera o nome de quem já existe.
    assert usuario.nome == "Maria Silva"
    assert len(eventos(db, "cadastro_automatico")) == 1
    assert len(eventos(db, "login")) == 2


def test_dominio_digesto_tambem_entra(cliente):
    assert entrar(cliente, "joao@digesto.com.br", "João")["email"] == "joao@digesto.com.br"


def test_dominio_nao_autorizado_e_recusado_e_registrado(cliente, db):
    resposta = cliente.post("/api/auth/teste/entrar", json={"email": "alguem@gmail.com", "nome": "Alguém"})

    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Use sua conta da Jusbrasil ou da Digesto para entrar."
    assert db.scalar(select(func.count()).select_from(Usuario)) == 0
    [falha] = eventos(db, "login_falha")
    assert falha.detalhes["motivo"] == "dominio_nao_autorizado"
    assert falha.detalhes["email"] == "alguem@gmail.com"
    assert "gerenciador_sessao" not in resposta.cookies


def test_subdominio_nao_e_aceito(cliente):
    resposta = cliente.post("/api/auth/teste/entrar", json={"email": "x@mail.jusbrasil.com.br", "nome": "X"})
    assert resposta.status_code == 403


@pytest.mark.parametrize("email", ["", "sem-arroba", "a@b", "duas@@jusbrasil.com.br"])
def test_email_invalido(cliente, email):
    resposta = cliente.post("/api/auth/teste/entrar", json={"email": email, "nome": "X"})
    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Informe um e-mail válido."


def test_nome_obrigatorio_no_primeiro_acesso(cliente):
    resposta = cliente.post("/api/auth/teste/entrar", json={"email": "novo@jusbrasil.com.br", "nome": "  "})
    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Informe o nome."


def test_cookie_de_sessao_protegido(cliente):
    resposta = cliente.post("/api/auth/teste/entrar", json={"email": "a@jusbrasil.com.br", "nome": "A"})
    cabecalho = resposta.headers["set-cookie"].lower()
    assert "gerenciador_sessao=" in cabecalho
    assert "httponly" in cabecalho
    assert "samesite=lax" in cabecalho
    assert f"max-age={15 * 24 * 3600}" in cabecalho


def test_eu_sem_sessao_responde_401(cliente):
    resposta = cliente.get("/api/eu")
    assert resposta.status_code == 401
    assert resposta.json()["detail"] == "Sua sessão terminou. Entre de novo."


def test_pedido_que_muda_dados_sem_cabecalho_e_recusado(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as sem_cabecalho:
        resposta = sem_cabecalho.post("/api/auth/teste/entrar", json={"email": "a@jusbrasil.com.br", "nome": "A"})
    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Pedido recusado."


def test_login_de_teste_desligado_nao_existe(cliente, monkeypatch):
    monkeypatch.setattr(obter_config(), "login_teste_habilitado", False)
    resposta = cliente.post("/api/auth/teste/entrar", json={"email": "a@jusbrasil.com.br", "nome": "A"})
    assert resposta.status_code == 404
    assert cliente.get("/api/auth/provedores").json() == {"teste": False, "google": False}


def test_provedores_com_login_de_teste_ligado(cliente):
    assert cliente.get("/api/auth/provedores").json() == {"teste": True, "google": False}


def test_login_de_teste_nunca_liga_fora_do_desenvolvimento():
    cfg = Config(login_teste_habilitado=True, ambiente="producao")
    with pytest.raises(RuntimeError):
        cfg.validar()
