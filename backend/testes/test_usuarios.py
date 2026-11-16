"""Desativar e reativar usuários (ADM da plataforma) e lista de usuários."""

from conftest import entrar, eventos


def _id(cliente) -> str:
    return cliente.get("/api/eu").json()["id"]


def test_desativar_encerra_sessoes_na_hora_e_bloqueia_login(novo_cliente, cliente_adm, db):
    pessoa = novo_cliente()
    entrar(pessoa, "saindo@jusbrasil.com.br", "Saindo")
    pid = _id(pessoa)

    assert cliente_adm.post(f"/api/admin/usuarios/{pid}/desativar").status_code == 204

    assert pessoa.get("/api/eu").status_code == 401
    resposta = novo_cliente().post(
        "/api/auth/teste/entrar", json={"email": "saindo@jusbrasil.com.br", "nome": "Saindo"}
    )
    assert resposta.status_code == 403
    assert resposta.json()["detail"] == "Seu acesso está desativado. Fale com o ADM da plataforma."
    [evento] = eventos(db, "usuario_desativado")
    assert evento.detalhes == {"sessoes_encerradas": 1}
    assert eventos(db, "login_falha")[-1].detalhes["motivo"] == "usuario_desativado"


def test_reativar_volta_com_os_mesmos_papeis(novo_cliente, cliente_adm, db):
    pessoa = novo_cliente()
    entrar(pessoa, "volta@jusbrasil.com.br", "Volta")
    pid = _id(pessoa)
    cliente_adm.post(f"/api/admin/usuarios/{pid}/papeis", json={"papel": "gestor"})
    cliente_adm.post(f"/api/admin/usuarios/{pid}/desativar")

    assert cliente_adm.post(f"/api/admin/usuarios/{pid}/reativar").status_code == 204

    eu = entrar(novo_cliente(), "volta@jusbrasil.com.br")
    assert eu["papeis"] == ["gestor"]
    assert len(eventos(db, "usuario_reativado")) == 1


def test_desativado_nao_aparece_como_adm_ativo_nem_recebe_papel(novo_cliente, cliente_adm):
    pessoa = novo_cliente()
    entrar(pessoa, "x@jusbrasil.com.br", "X")
    pid = _id(pessoa)
    cliente_adm.post(f"/api/admin/usuarios/{pid}/desativar")

    resposta = cliente_adm.post(f"/api/admin/usuarios/{pid}/papeis", json={"papel": "gestor"})
    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "Reative o usuário antes de dar um papel a ele."


def test_so_adm_desativa(novo_cliente, cliente_adm):
    gestor, alvo = novo_cliente(), novo_cliente()
    entrar(gestor, "gestor@jusbrasil.com.br", "Gestor")
    entrar(alvo, "alvo@jusbrasil.com.br", "Alvo")
    cliente_adm.post(f"/api/admin/usuarios/{_id(gestor)}/papeis", json={"papel": "gestor"})

    assert gestor.post(f"/api/admin/usuarios/{_id(alvo)}/desativar").status_code == 403


def test_nao_desativa_a_si_mesmo(cliente_adm, adm):
    resposta = cliente_adm.post(f"/api/admin/usuarios/{adm.id}/desativar")
    assert resposta.status_code == 409
    assert resposta.json()["detail"] == "Você não pode desativar o seu próprio usuário."


def test_desativar_ou_reativar_duas_vezes(novo_cliente, cliente_adm):
    pessoa = novo_cliente()
    entrar(pessoa, "d@jusbrasil.com.br", "Davi")
    pid = _id(pessoa)

    assert cliente_adm.post(f"/api/admin/usuarios/{pid}/reativar").json()["detail"] == "Davi já está ativo."
    cliente_adm.post(f"/api/admin/usuarios/{pid}/desativar")
    assert cliente_adm.post(f"/api/admin/usuarios/{pid}/desativar").json()["detail"] == "Davi já está desativado."


def test_lista_de_usuarios_com_papeis_e_busca(novo_cliente, cliente_adm):
    for email, nome in [("bruno.reis@jusbrasil.com.br", "Bruno Reis"), ("carla@digesto.com.br", "Carla Souza")]:
        entrar(novo_cliente(), email, nome)

    todos = cliente_adm.get("/api/admin/usuarios").json()
    assert [u["nome"] for u in todos] == ["Ana Adm", "Bruno Reis", "Carla Souza"]
    assert todos[0]["papeis"] == ["adm_plataforma"]
    assert todos[1]["ativo"] is True

    assert [u["nome"] for u in cliente_adm.get("/api/admin/usuarios", params={"busca": "souza"}).json()] == [
        "Carla Souza"
    ]
    assert [u["nome"] for u in cliente_adm.get("/api/admin/usuarios", params={"busca": "DIGESTO"}).json()] == [
        "Carla Souza"
    ]
