"""Consulta da auditoria e configuração dos domínios autorizados."""

from conftest import entrar, eventos
from starlette.requests import Request

from gerenciador.api.deps import ip_do_pedido

# --- Auditoria ------------------------------------------------------------------------------


def test_auditoria_do_mais_recente_para_o_mais_antigo_com_paginas(novo_cliente, cliente_adm):
    for i in range(3):
        entrar(novo_cliente(), f"p{i}@jusbrasil.com.br", f"P{i}")

    pagina = cliente_adm.get("/api/admin/auditoria", params={"limite": 4}).json()
    ids = [e["id"] for e in pagina["eventos"]]
    assert ids == sorted(ids, reverse=True)
    assert len(ids) == 4
    assert pagina["proximo"] == ids[-1]

    resto = cliente_adm.get("/api/admin/auditoria", params={"limite": 4, "antes_de": pagina["proximo"]}).json()
    assert all(e["id"] < ids[-1] for e in resto["eventos"])
    assert resto["proximo"] is None


def test_auditoria_filtra_por_tipo_e_por_pessoa(novo_cliente, cliente_adm):
    pessoa = novo_cliente()
    entrar(pessoa, "f@jusbrasil.com.br", "F")
    pid = pessoa.get("/api/eu").json()["id"]
    novo_cliente().post("/api/auth/teste/entrar", json={"email": "z@gmail.com", "nome": "Z"})

    falhas = cliente_adm.get("/api/admin/auditoria", params={"tipo": "login_falha"}).json()["eventos"]
    assert [e["detalhes"]["email"] for e in falhas] == ["z@gmail.com"]

    da_pessoa = cliente_adm.get("/api/admin/auditoria", params={"usuario_id": pid}).json()["eventos"]
    assert [e["tipo"] for e in da_pessoa] == ["login", "cadastro_automatico"]
    assert da_pessoa[0]["ator"]["nome"] == "F"


def test_gestor_ve_auditoria_e_usuario_comum_nao(novo_cliente, cliente_adm):
    gestor, comum = novo_cliente(), novo_cliente()
    entrar(gestor, "g@jusbrasil.com.br", "G")
    entrar(comum, "c@jusbrasil.com.br", "C")
    cliente_adm.post(f"/api/admin/usuarios/{gestor.get('/api/eu').json()['id']}/papeis", json={"papel": "gestor"})

    assert gestor.get("/api/admin/auditoria").status_code == 200
    assert comum.get("/api/admin/auditoria").status_code == 403


def _pedido(cliente_ip: str, encaminhado: str | None) -> Request:
    cabecalhos = [(b"x-forwarded-for", encaminhado.encode())] if encaminhado else []
    return Request({"type": "http", "client": (cliente_ip, 1234), "headers": cabecalhos})


def test_ip_encaminhado_so_vale_vindo_da_propria_maquina():
    assert ip_do_pedido(_pedido("127.0.0.1", "10.0.0.5, 1.1.1.1")) == "10.0.0.5"
    assert ip_do_pedido(_pedido("::1", "10.0.0.6")) == "10.0.0.6"
    assert ip_do_pedido(_pedido("200.1.2.3", "10.0.0.5")) == "200.1.2.3"
    assert ip_do_pedido(_pedido("200.1.2.3", None)) == "200.1.2.3"


# --- Domínios -------------------------------------------------------------------------------


def test_adm_adiciona_dominio_e_quem_e_dele_passa_a_entrar(novo_cliente, cliente_adm, db):
    recusado = novo_cliente().post("/api/auth/teste/entrar", json={"email": "a@novaempresa.com.br", "nome": "A"})
    assert recusado.status_code == 403

    assert cliente_adm.post("/api/admin/dominios", json={"dominio": "@NovaEmpresa.com.br "}).status_code == 204

    entrar(novo_cliente(), "a@novaempresa.com.br", "A")
    nomes = [d["dominio"] for d in cliente_adm.get("/api/admin/dominios").json()]
    assert nomes == ["digesto.com.br", "jusbrasil.com.br", "novaempresa.com.br"]
    assert eventos(db, "dominio_adicionado")[0].detalhes == {"dominio": "novaempresa.com.br"}


def test_dominio_invalido_ou_repetido(cliente_adm):
    invalido = cliente_adm.post("/api/admin/dominios", json={"dominio": "nao é domínio"})
    assert invalido.status_code == 409
    assert invalido.json()["detail"] == "Informe um domínio válido, como jusbrasil.com.br."
    repetido = cliente_adm.post("/api/admin/dominios", json={"dominio": "digesto.com.br"})
    assert repetido.json()["detail"] == "O domínio digesto.com.br já está autorizado."


def test_remover_dominio_bloqueia_novos_logins(novo_cliente, cliente_adm, db):
    assert cliente_adm.delete("/api/admin/dominios/digesto.com.br").status_code == 204
    resposta = novo_cliente().post("/api/auth/teste/entrar", json={"email": "a@digesto.com.br", "nome": "A"})
    assert resposta.status_code == 403
    assert len(eventos(db, "dominio_removido")) == 1


def test_nao_remove_o_dominio_do_proprio_email_nem_o_ultimo(cliente_adm):
    proprio = cliente_adm.delete("/api/admin/dominios/jusbrasil.com.br")
    assert proprio.status_code == 409
    assert proprio.json()["detail"] == "Você não pode remover o domínio do seu próprio e-mail."
    assert cliente_adm.delete("/api/admin/dominios/inexistente.com").status_code == 404


def test_ultimo_dominio_nao_pode_ser_removido(db, adm):
    from gerenciador import dominios
    from gerenciador.erros import OperacaoNegada

    dominios.remover(db, adm, "digesto.com.br", None)
    try:
        # Sobra só o domínio do próprio ADM; a regra do último domínio vem antes.
        dominios.remover(db, adm, "jusbrasil.com.br", None)
    except OperacaoNegada as erro:
        assert erro.mensagem == "Pelo menos um domínio precisa continuar autorizado."
    else:
        raise AssertionError("deveria ter recusado")


def test_gestor_nao_configura_dominios(novo_cliente, cliente_adm):
    gestor = novo_cliente()
    entrar(gestor, "g@jusbrasil.com.br", "G")
    cliente_adm.post(f"/api/admin/usuarios/{gestor.get('/api/eu').json()['id']}/papeis", json={"papel": "gestor"})

    assert gestor.get("/api/admin/dominios").status_code == 403
    assert gestor.post("/api/admin/dominios", json={"dominio": "x.com.br"}).status_code == 403
