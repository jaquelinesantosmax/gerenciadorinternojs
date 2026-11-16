"""Etapa 4: matriz completa do espaço, times, Gestor, suporte do ADM da plataforma, Solicitar acesso,
espaço aberto e compartilhamento do espaço pessoal."""

from conftest import criar_item, criar_projeto, entrar, eventos

from gerenciador import relogio


def _id(cliente) -> str:
    return cliente.get("/api/eu").json()["id"]


def _pessoa(novo_cliente, email, nome):
    c = novo_cliente()
    entrar(c, email, nome)
    return c, _id(c)


def _dar_papel(cliente_adm, usuario_id, papel):
    assert cliente_adm.post(f"/api/admin/usuarios/{usuario_id}/papeis", json={"papel": papel}).status_code == 204


# --- Times ------------------------------------------------------------------------------------

def test_times_quem_cria_e_quem_edita(cenario, novo_cliente):
    c = cenario
    comum, comum_id = _pessoa(novo_cliente, "comum@jusbrasil.com.br", "Comum")
    assert comum.post("/api/times", json={"nome": "Sem permissão"}).status_code == 403
    # Quem é ADM de algum espaço cria time.
    criador, criador_id = _pessoa(novo_cliente, "criador@jusbrasil.com.br", "Criador")
    c["adm"].post("/api/espacos/LOP/membros", json={"usuario_id": criador_id, "papel": "adm"})
    time = criador.post("/api/times", json={"nome": "Suporte B2B"}).json()
    assert time["pode_editar"] is True
    assert criador.post(f"/api/times/{time['id']}/membros", json={"usuario_id": comum_id}).status_code == 204
    # Outra pessoa (não criadora, não Gestor) não edita o time.
    assert c["membro"].post(f"/api/times/{time['id']}/membros", json={"usuario_id": c["membro_id"]}).status_code == 403
    gestao = comum.get("/api/times/gestao").json()
    assert gestao["pode_criar"] is False
    suporte = next(t for t in gestao["times"] if t["nome"] == "Suporte B2B")
    assert [p["nome"] for p in suporte["membros"]] == ["Comum"] and suporte["pode_editar"] is False


def test_acesso_por_time_entra_e_sai_junto_com_o_time(cenario, novo_cliente, db):
    c = cenario
    pessoa, pessoa_id = _pessoa(novo_cliente, "time@jusbrasil.com.br", "Pessoa do Time")
    time = c["adm"].post("/api/times", json={"nome": "Juridico"}).json()
    assert pessoa.get("/api/espacos/LOP").status_code == 404
    assert c["adm"].post("/api/espacos/LOP/times-acesso", json={"time_id": time["id"], "papel": "membro"}).status_code == 204
    c["adm"].post(f"/api/times/{time['id']}/membros", json={"usuario_id": pessoa_id})
    detalhe = pessoa.get("/api/espacos/LOP").json()
    assert detalhe["meu_papel"] == "membro" and detalhe["permissoes"]["criar_itens"] is True
    # Pessoa do time pode ser responsável por item.
    criar_item(c["adm"], c, responsavel_id=pessoa_id)
    c["adm"].delete(f"/api/times/{time['id']}/membros/{pessoa_id}")
    assert pessoa.get("/api/espacos/LOP").status_code == 404
    assert [e.tipo for e in eventos(db) if e.tipo.startswith("time_")][-3:] == [
        "time_acesso_dado", "time_membro_adicionado", "time_membro_removido"]


def test_vale_o_maior_papel_entre_individual_e_time(cenario):
    c = cenario
    time = c["adm"].post("/api/times", json={"nome": "Leads"}).json()
    c["adm"].post(f"/api/times/{time['id']}/membros", json={"usuario_id": c["leitor_id"]})
    c["adm"].post("/api/espacos/LOP/times-acesso", json={"time_id": time["id"], "papel": "adm"})
    detalhe = c["leitor"].get("/api/espacos/LOP").json()
    assert detalhe["meu_papel"] == "adm" and detalhe["permissoes"]["configurar"] is True


def test_espaco_nao_fica_sem_adm_mesmo_com_time(cenario):
    c = cenario
    time = c["adm"].post("/api/times", json={"nome": "Admins"}).json()
    c["adm"].post(f"/api/times/{time['id']}/membros", json={"usuario_id": c["membro_id"]})
    c["adm"].post("/api/espacos/LOP/times-acesso", json={"time_id": time["id"], "papel": "adm"})
    # Com o time de ADMs, o ADM direto pode virar Membro.
    assert c["adm"].patch(f"/api/espacos/LOP/membros/{c['adm_id']}", json={"papel": "membro"}).status_code == 204
    r = c["membro"].delete(f"/api/espacos/LOP/times-acesso/{time['id']}")
    assert r.json()["detail"] == "O espaço precisa ter pelo menos um ADM."


# --- Gestor -----------------------------------------------------------------------------------

def test_gestor_abre_qualquer_espaco_de_equipe_e_escolhe_acompanhar(cenario, novo_cliente):
    c = cenario
    gestor, gestor_id = _pessoa(novo_cliente, "gestor@jusbrasil.com.br", "Gina Gestora")
    _dar_papel(c["adm"], gestor_id, "gestor")
    detalhe = gestor.get("/api/espacos/LOP").json()
    assert detalhe["meu_papel"] == "gestor" and detalhe["pode_acompanhar"] is True and detalhe["acompanha"] is False
    p = detalhe["permissoes"]
    assert p["configurar"] and p["gerenciar_membros"] and p["aprovar_acesso"] and p["criar_itens"]
    assert not p["gerenciar_sprints"] and not p["marcar_aberto"] and not p["excluir_qualquer_item"]
    # Ainda não aparece no menu dele; depois de "Acompanhar", aparece e o ADM e o Membro veem.
    assert [e["sigla"] for e in gestor.get("/api/espacos").json()] == []
    assert gestor.put("/api/espacos/LOP/acompanhar", json={"sim": True}).status_code == 204
    assert [e["sigla"] for e in gestor.get("/api/espacos").json()] == ["LOP"]
    assert [g["pessoa"]["nome"] for g in c["membro"].get("/api/espacos/LOP/gestores").json()] == ["Gina Gestora"]
    assert c["leitor"].get("/api/espacos/LOP/gestores").status_code == 403


def test_gestor_nunca_ve_espaco_pessoal(cenario, novo_cliente):
    c = cenario
    gestor, gestor_id = _pessoa(novo_cliente, "gestor@jusbrasil.com.br", "Gestor")
    _dar_papel(c["adm"], gestor_id, "gestor")
    c["membro"].post("/api/espacos", json={"tipo": "pessoal", "nome": "Meu", "sigla": "MEU"})
    assert gestor.get("/api/espacos/MEU").status_code == 404
    assert "MEU" not in [e["sigla"] for e in gestor.get("/api/explorar").json()]


# --- Suporte do ADM da plataforma -------------------------------------------------------------

def test_suporte_por_4_horas_com_motivo_e_auditoria(cliente_adm, novo_cliente, db, relogio_falso, adm):
    dona, _ = _pessoa(novo_cliente, "dona@jusbrasil.com.br", "Dona")
    _dar_papel(cliente_adm, _id(dona), "criar_espacos")
    criar_projeto(dona, sigla="PRV", nome="Privado")
    assert cliente_adm.get("/api/espacos/PRV").status_code == 404
    sem_motivo = cliente_adm.post("/api/espacos/PRV/suporte", json={"motivo": " "})
    assert sem_motivo.json()["detail"] == "Informe o motivo do suporte."
    assert cliente_adm.post("/api/espacos/PRV/suporte", json={"motivo": "Chamado 123"}).status_code == 204
    detalhe = cliente_adm.get("/api/espacos/PRV").json()
    assert detalhe["meu_papel"] == "suporte" and detalhe["permissoes"]["configurar"] is True
    cliente_adm.patch("/api/espacos/PRV", json={"descricao": "ajustado no suporte"})
    [inicio] = eventos(db, "suporte_iniciado")
    assert inicio.detalhes["motivo"] == "Chamado 123"
    acao = eventos(db, "acao_em_suporte")[-1]
    assert acao.detalhes["metodo"] == "PATCH" and acao.detalhes["caminho"] == "/api/espacos/PRV"
    relogio_falso.avancar(hours=4, minutes=1)
    assert cliente_adm.get("/api/espacos/PRV").status_code == 404
    # Só o ADM da plataforma entra para suporte.
    assert dona.post("/api/espacos/PRV/suporte", json={"motivo": "x"}).status_code == 403


# --- Solicitar acesso -------------------------------------------------------------------------

def test_solicitar_acesso_pelo_item_restrito_e_aprovar_escolhendo_o_papel(cenario, novo_cliente, db):
    c = cenario
    # Item do espaço LOP vinculado a um item de outro espaço que a pessoa vê.
    outro_adm, outro_id = _pessoa(novo_cliente, "outro@jusbrasil.com.br", "Outra ADM")
    _dar_papel(c["adm"], outro_id, "criar_espacos")
    criar_projeto(outro_adm, sigla="OUT", nome="Outro")
    # Quem vincula precisa ver os dois itens: a ADM do LOP também é Membro do OUT.
    outro_adm.post("/api/espacos/OUT/membros", json={"usuario_id": c["adm_id"], "papel": "membro"})
    restrito = criar_item(c["adm"], c, resumo="Segredo")
    meu = criar_item(outro_adm, c, sigla="OUT", responsavel_id=outro_id, time_id=c["time"])
    r = c["adm"].post(f"/api/itens/{meu['chave']}/vinculos", json={"tipo": "relacionado", "chave": restrito["chave"]})
    assert r.status_code == 201, r.text
    # A Outra ADM não vê o LOP: o vínculo aparece restrito, e ela pede acesso.
    [v] = outro_adm.get(f"/api/itens/{meu['chave']}").json()["vinculos"]
    assert v["acesso_restrito"] is True and v["pedido_pendente"] is False
    assert outro_adm.post(f"/api/itens/{restrito['chave']}/solicitar-acesso", json={"mensagem": "Preciso ver"}).status_code == 204
    [v] = outro_adm.get(f"/api/itens/{meu['chave']}").json()["vinculos"]
    assert v["pedido_pendente"] is True
    # Pedido repetido não duplica.
    outro_adm.post(f"/api/itens/{restrito['chave']}/solicitar-acesso", json={})
    [pedido] = c["adm"].get("/api/espacos/LOP/pedidos").json()
    assert pedido["pessoa"]["nome"] == "Outra ADM" and pedido["item_chave"] == restrito["chave"]
    assert c["membro"].get("/api/espacos/LOP/pedidos").status_code == 403
    # Aprovar exige escolher o papel.
    assert c["adm"].post(f"/api/espacos/LOP/pedidos/{pedido['id']}/aprovar", json={"papel": ""}).status_code == 400
    assert c["adm"].post(f"/api/espacos/LOP/pedidos/{pedido['id']}/aprovar", json={"papel": "leitor"}).status_code == 204
    assert outro_adm.get("/api/espacos/LOP").json()["meu_papel"] == "leitor"
    assert c["adm"].get("/api/espacos/LOP/pedidos").json() == []
    assert eventos(db, "membro_adicionado")[-1].detalhes["por_pedido"] is True


def test_leitor_pede_para_virar_membro_e_pedido_pode_ser_recusado(cenario, db):
    c = cenario
    assert c["leitor"].post("/api/espacos/LOP/solicitar-acesso", json={}).status_code == 204
    assert c["leitor"].get("/api/espacos/LOP").json()["pedido_pendente"] is True
    [pedido] = c["adm"].get("/api/espacos/LOP/pedidos").json()
    assert c["adm"].post(f"/api/espacos/LOP/pedidos/{pedido['id']}/recusar").status_code == 204
    assert len(eventos(db, "pedido_acesso_recusado")) == 1
    assert c["membro"].post("/api/espacos/LOP/solicitar-acesso", json={}).json()["detail"] == "Você já é Membro deste espaço."


# --- Espaço aberto ----------------------------------------------------------------------------

def test_espaco_aberto_para_toda_a_empresa(cenario, novo_cliente, db):
    c = cenario
    qualquer, _ = _pessoa(novo_cliente, "qualquer@digesto.com.br", "Qualquer")
    item = criar_item(c["adm"], c)
    assert qualquer.get(f"/api/itens/{item['chave']}").status_code == 404
    assert c["membro"].put("/api/espacos/LOP/aberto", json={"aberto": True}).status_code == 403
    assert c["adm"].put("/api/espacos/LOP/aberto", json={"aberto": True}).status_code == 204
    assert [e["sigla"] for e in qualquer.get("/api/explorar").json()] == ["LOP"]
    detalhe = qualquer.get("/api/espacos/LOP").json()
    assert detalhe["meu_papel"] == "aberto"
    p = detalhe["permissoes"]
    assert p["ver"] and p["comentar"] and p["anexar"] and not p["criar_itens"] and not p["vincular"]
    url = f"/api/itens/{item['chave']}"
    assert qualquer.post(f"{url}/comentarios", json={"corpo": {"type": "doc", "content": [
        {"type": "paragraph", "content": [{"type": "text", "text": "Comentário de fora"}]}]}}).status_code == 201
    assert qualquer.patch(url, json={"dados": {"resumo": "x"}}).status_code == 403
    assert eventos(db, "espaco_aberto")


# --- Espaço pessoal compartilhado -------------------------------------------------------------

def test_espaco_pessoal_compartilhado_so_leitura(cenario, novo_cliente):
    c = cenario
    dono, _ = _pessoa(novo_cliente, "dono@jusbrasil.com.br", "Dono")
    dono.post("/api/espacos", json={"tipo": "pessoal", "nome": "Minhas", "sigla": "MINHA"})
    item = criar_item(dono, c, sigla="MINHA", responsavel_id=_id(dono))
    assert c["membro"].get(f"/api/itens/{item['chave']}").status_code == 404
    assert dono.post("/api/espacos/MINHA/compartilhamentos", json={"usuario_id": c["membro_id"]}).status_code == 204
    assert [p["nome"] for p in dono.get("/api/espacos/MINHA/compartilhamentos").json()] == ["Marta Membro"]
    detalhe = c["membro"].get("/api/espacos/MINHA").json()
    assert detalhe["meu_papel"] == "compartilhado"
    assert not detalhe["permissoes"]["comentar"] and not detalhe["permissoes"]["editar_itens"]
    assert c["membro"].get(f"/api/itens/{item['chave']}").status_code == 200
    assert "MINHA" in [e["sigla"] for e in c["membro"].get("/api/espacos").json()]
    assert c["membro"].post("/api/espacos/MINHA/compartilhamentos", json={"usuario_id": c["leitor_id"]}).status_code == 403
    dono.delete(f"/api/espacos/MINHA/compartilhamentos/{c['membro_id']}")
    assert c["membro"].get("/api/espacos/MINHA").status_code == 404


def test_explorar_para_adm_da_plataforma_lista_todos_os_de_equipe(cenario, novo_cliente):
    c = cenario
    dona, dona_id = _pessoa(novo_cliente, "dona@jusbrasil.com.br", "Dona")
    _dar_papel(c["adm"], dona_id, "criar_espacos")
    criar_projeto(dona, sigla="PRV", nome="Privado")
    lista = {e["sigla"]: e for e in c["adm"].get("/api/explorar").json()}
    assert set(lista) == {"LOP", "PRV"}
    assert lista["PRV"]["meu_papel"] is None and lista["LOP"]["meu_papel"] == "adm"
    assert relogio  # módulo usado pelos testes de tempo
