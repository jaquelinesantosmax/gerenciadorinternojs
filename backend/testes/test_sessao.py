"""Sessão de 15 dias que renova a cada uso (decisão de 16/11) e saída."""

from conftest import entrar, eventos
from sqlalchemy import select

from gerenciador import sessoes
from gerenciador.modelos import Sessao


def test_sessao_renova_a_cada_uso(cliente, relogio_falso):
    entrar(cliente, "a@jusbrasil.com.br", "A")

    relogio_falso.avancar(days=14)
    assert cliente.get("/api/eu").status_code == 200
    relogio_falso.avancar(days=14)
    # 28 dias depois do login, mas só 14 desde o último uso: continua valendo.
    assert cliente.get("/api/eu").status_code == 200


def test_sessao_cai_depois_de_15_dias_sem_uso(cliente, relogio_falso):
    entrar(cliente, "a@jusbrasil.com.br", "A")

    relogio_falso.avancar(days=15, seconds=1)
    assert cliente.get("/api/eu").status_code == 401


def test_renovacao_regrava_o_cookie(cliente, relogio_falso):
    entrar(cliente, "a@jusbrasil.com.br", "A")
    relogio_falso.avancar(minutes=6)
    resposta = cliente.get("/api/eu")
    assert "gerenciador_sessao=" in resposta.headers.get("set-cookie", "")


def test_uso_seguido_nao_grava_no_banco_a_cada_clique(cliente, relogio_falso, db):
    entrar(cliente, "a@jusbrasil.com.br", "A")
    expira_antes = db.scalar(select(Sessao)).expira_em

    relogio_falso.avancar(minutes=2)
    resposta = cliente.get("/api/eu")
    assert resposta.status_code == 200
    assert "set-cookie" not in resposta.headers
    db.expire_all()
    assert db.scalar(select(Sessao)).expira_em == expira_antes


def test_banco_guarda_so_o_hash_do_token(cliente, db):
    entrar(cliente, "a@jusbrasil.com.br", "A")
    token = cliente.cookies.get(sessoes.NOME_COOKIE)
    sessao = db.scalar(select(Sessao))
    assert token and sessao.token_hash != token
    assert len(sessao.token_hash) == 64


def test_sair_encerra_a_sessao(cliente, db):
    entrar(cliente, "a@jusbrasil.com.br", "A")
    token = cliente.cookies.get(sessoes.NOME_COOKIE)

    resposta = cliente.post("/api/auth/sair")
    assert resposta.status_code == 204
    assert cliente.get("/api/eu").status_code == 401
    # Mesmo quem guardou o token antigo não consegue mais usar.
    cliente.cookies.set(sessoes.NOME_COOKIE, token)
    assert cliente.get("/api/eu").status_code == 401
    assert len(eventos(db, "logout")) == 1
    assert db.scalar(select(Sessao)).motivo_encerramento == "logout"


def test_sair_sem_sessao_nao_quebra(cliente, db):
    assert cliente.post("/api/auth/sair").status_code == 204
    assert eventos(db, "logout") == []


def test_token_inventado_nao_entra(cliente):
    cliente.cookies.set(sessoes.NOME_COOKIE, "token-inventado")
    assert cliente.get("/api/eu").status_code == 401


def test_cada_navegador_tem_sua_sessao(novo_cliente):
    computador, celular = novo_cliente(), novo_cliente()
    entrar(computador, "a@jusbrasil.com.br", "A")
    entrar(celular, "a@jusbrasil.com.br", "A")

    computador.post("/api/auth/sair")
    assert computador.get("/api/eu").status_code == 401
    assert celular.get("/api/eu").status_code == 200
