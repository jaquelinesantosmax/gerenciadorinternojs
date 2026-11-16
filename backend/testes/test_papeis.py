"""Papéis da plataforma: ADM da plataforma, Gestor e permissão de criar espaços."""

import pytest
from conftest import entrar, eventos

from gerenciador.cli import main as cli
from gerenciador.erros import OperacaoNegada
from gerenciador.modelos import Papel
from gerenciador.papeis import PERMISSOES, cadastrar_adm_instalacao, permissoes_de


def _id(cliente) -> str:
    return cliente.get("/api/eu").json()["id"]


def _conceder(cliente, usuario_id, papel):
    return cliente.post(f"/api/admin/usuarios/{usuario_id}/papeis", json={"papel": papel})


def _revogar(cliente, usuario_id, papel):
    return cliente.delete(f"/api/admin/usuarios/{usuario_id}/papeis/{papel}")


# --- Instalação -----------------------------------------------------------------------------

def test_adm_da_instalacao_e_registrado(adm, db):
    [evento] = eventos(db, "adm_instalacao")
    assert evento.alvo_usuario_id == adm.id
    assert evento.ator_id is None


def test_cadastro_de_adm_na_instalacao_pode_ser_repetido(adm, db):
    cadastrar_adm_instalacao(db, adm.email, adm.nome)
    assert len(eventos(db, "adm_instalacao")) == 1


def test_adm_da_instalacao_precisa_de_dominio_autorizado(db):
    with pytest.raises(OperacaoNegada):
        cadastrar_adm_instalacao(db, "alguem@gmail.com", "Alguém")


def test_comando_criar_adm(db, capsys):
    assert cli(["criar-adm", "--email", "Bia@Jusbrasil.com.br", "--nome", "Bia"]) == 0
    assert "Bia (bia@jusbrasil.com.br) é ADM da plataforma" in capsys.readouterr().out
    assert cli(["criar-adm", "--email", "x@gmail.com", "--nome", "X"]) == 1


def test_adm_ve_todas_as_permissoes_da_etapa(cliente_adm):
    eu = cliente_adm.get("/api/eu").json()
    assert eu["papeis"] == ["adm_plataforma"]
    assert all(eu["permissoes"].values())


# --- Matriz de permissões -------------------------------------------------------------------

def test_matriz_da_plataforma():
    gestor = permissoes_de({Papel.GESTOR})
    criar = permissoes_de({Papel.CRIAR_ESPACOS})
    comum = permissoes_de(set())

    assert gestor == {
        "configurar_dominios": False,
        "dar_tirar_adm_plataforma": False,
        "dar_tirar_gestor": True,
        "dar_tirar_criar_espacos": True,
        "desativar_usuarios": False,
        "ver_auditoria": True,
        "ver_usuarios": True,
        "criar_espaco_equipe": True,
        "acessar_espaco_gestao": True,
        "criar_time": True,
        "definir_limite_anexos": False,
        "gerenciar_status_padrao": False,
    }
    assert [k for k, v in criar.items() if v] == ["criar_espaco_equipe", "criar_time"]
    assert not any(comum.values())
    assert set(permissoes_de({Papel.ADM_PLATAFORMA})) == set(PERMISSOES)


# --- Conceder e revogar ---------------------------------------------------------------------

def test_usuario_comum_nao_ve_usuarios_nem_concede(novo_cliente, cliente_adm):
    comum = novo_cliente()
    entrar(comum, "comum@jusbrasil.com.br", "Comum")

    assert comum.get("/api/admin/usuarios").status_code == 403
    resposta = _conceder(comum, _id(comum), "gestor")
    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Você não tem permissão para esta ação."


def test_adm_concede_gestor_e_fica_registrado(novo_cliente, cliente_adm, adm, db):
    pessoa = novo_cliente()
    entrar(pessoa, "gi@jusbrasil.com.br", "Gi")
    pessoa_id = _id(pessoa)

    assert _conceder(cliente_adm, pessoa_id, "gestor").status_code == 204

    eu = pessoa.get("/api/eu").json()
    assert eu["papeis"] == ["gestor"]
    assert eu["permissoes"]["acessar_espaco_gestao"] is True
    [evento] = eventos(db, "papel_concedido")
    assert str(evento.alvo_usuario_id) == pessoa_id
    assert evento.ator_id == adm.id
    assert evento.detalhes == {"papel": "gestor"}


def test_gestor_da_e_tira_gestor_e_criar_espacos_mas_nao_adm(novo_cliente, cliente_adm):
    gestor, outro = novo_cliente(), novo_cliente()
    entrar(gestor, "gestor@jusbrasil.com.br", "Gestor")
    entrar(outro, "outro@digesto.com.br", "Outro")
    _conceder(cliente_adm, _id(gestor), "gestor")
    outro_id = _id(outro)

    assert _conceder(gestor, outro_id, "gestor").status_code == 204
    assert _conceder(gestor, outro_id, "criar_espacos").status_code == 204
    assert _revogar(gestor, outro_id, "gestor").status_code == 204
    assert _conceder(gestor, outro_id, "adm_plataforma").status_code == 403
    assert outro.get("/api/eu").json()["papeis"] == ["criar_espacos"]


def test_nao_concede_papel_repetido_nem_revoga_o_que_nao_existe(novo_cliente, cliente_adm):
    pessoa = novo_cliente()
    entrar(pessoa, "p@jusbrasil.com.br", "Paula")
    pid = _id(pessoa)
    _conceder(cliente_adm, pid, "gestor")

    repetido = _conceder(cliente_adm, pid, "gestor")
    assert repetido.status_code == 409
    assert repetido.json()["detail"] == "Paula já tem o papel Gestor."
    inexistente = _revogar(cliente_adm, pid, "criar_espacos")
    assert inexistente.status_code == 409
    assert inexistente.json()["detail"] == "Paula não tem o papel Criar espaços."


def test_papel_desconhecido_e_usuario_inexistente(cliente_adm):
    assert _conceder(cliente_adm, _id(cliente_adm), "dono").status_code == 422
    resposta = _conceder(cliente_adm, "00000000-0000-0000-0000-000000000000", "gestor")
    assert resposta.status_code == 404


def test_plataforma_nunca_fica_sem_adm(novo_cliente, cliente_adm, adm):
    resposta = _revogar(cliente_adm, adm.id, "adm_plataforma")
    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "A plataforma precisa ter pelo menos um ADM da plataforma."

    segundo = novo_cliente()
    entrar(segundo, "segundo@jusbrasil.com.br", "Segundo")
    assert _conceder(cliente_adm, _id(segundo), "adm_plataforma").status_code == 204
    # Com dois ADMs, um pode sair.
    assert _revogar(segundo, adm.id, "adm_plataforma").status_code == 204
    assert cliente_adm.get("/api/eu").json()["papeis"] == []


def test_lista_de_gestores_mostra_quem_concedeu_e_quando(novo_cliente, cliente_adm, adm, relogio_falso):
    pessoa = novo_cliente()
    entrar(pessoa, "g@jusbrasil.com.br", "Gabi")
    _conceder(cliente_adm, _id(pessoa), "gestor")

    [gestor] = cliente_adm.get("/api/admin/gestores").json()
    assert gestor["usuario"]["nome"] == "Gabi"
    assert gestor["concedido_por"]["email"] == adm.email
    assert gestor["concedido_em"].startswith("2026-11-16T12:00:00")

    _revogar(cliente_adm, _id(pessoa), "gestor")
    assert cliente_adm.get("/api/admin/gestores").json() == []


def test_usuario_comum_nao_ve_lista_de_gestores(cliente):
    entrar(cliente, "c@jusbrasil.com.br", "C")
    assert cliente.get("/api/admin/gestores").status_code == 403


def test_papel_volta_a_valer_quando_concedido_de_novo(novo_cliente, cliente_adm):
    pessoa = novo_cliente()
    entrar(pessoa, "r@jusbrasil.com.br", "R")
    pid = _id(pessoa)
    _conceder(cliente_adm, pid, "criar_espacos")
    _revogar(cliente_adm, pid, "criar_espacos")
    assert _conceder(cliente_adm, pid, "criar_espacos").status_code == 204
    assert pessoa.get("/api/eu").json()["papeis"] == ["criar_espacos"]


def test_preparar_dados_completa_o_que_falta_e_pode_repetir(cliente_adm, db):
    from conftest import criar_projeto
    from sqlalchemy import delete

    from gerenciador.modelos_quadros import Quadro, StatusDoEspaco, Transicao
    from gerenciador.preparar_dados import preparar

    criar_projeto(cliente_adm)
    # Simula um espaço antigo, de antes da Etapa 3a.
    db.execute(delete(Quadro))
    db.execute(delete(Transicao))
    db.execute(delete(StatusDoEspaco))
    db.commit()
    assert preparar(db)["espacos"] == 1
    assert preparar(db) == {"espacos": 0, "paineis": 0, "itens": 0}
    assert len(cliente_adm.get("/api/espacos/LOP/workflow").json()["ligados"]) == 8
