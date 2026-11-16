"""Etapa 3a: status ligados no espaço, fluxo de transições, quadros, colunas e Gantt."""

import pytest
from conftest import criar_item, criar_projeto

from gerenciador.workflow import nome_parecido


def _wf(cliente, sigla="LOP"):
    return cliente.get(f"/api/espacos/{sigla}/workflow").json()


def _id_status(wf, nome):
    return next(s["id"] for s in wf["ligados"] if s["nome"] == nome)


def _mudar(cliente, chave, status_id, **extra):
    return cliente.patch(f"/api/itens/{chave}", json={"dados": {"status_id": status_id}, **extra})


# --- Status e fluxo ---------------------------------------------------------------------------

def test_espaco_nasce_com_8_status_e_o_fluxo_padrao(cenario):
    wf = _wf(cenario["adm"])
    assert [s["nome"] for s in wf["ligados"]] == [
        "Backlog", "A fazer", "Em andamento", "Em validação", "Aguardando terceiros", "Bloqueado", "Concluído", "Cancelado"]
    nomes = {s["id"]: s["nome"] for s in wf["ligados"]}
    pares = {(nomes[de], nomes[para]) for de, para in wf["transicoes"]}
    assert ("A fazer", "Em andamento") in pares
    assert ("Em validação", "Em andamento") in pares
    assert ("Concluído", "A fazer") in pares
    assert ("Bloqueado", "Cancelado") in pares
    assert ("A fazer", "Concluído") not in pares
    assert ("Concluído", "Cancelado") in pares


def test_item_segue_o_fluxo(cenario):
    c = cenario
    item = criar_item(c["adm"], c)
    pulo = _mudar(c["membro"], item["chave"], c["status"]["Concluído"])
    assert pulo.status_code == 400
    assert pulo.json()["detail"] == (
        "O fluxo não permite ir de A fazer para Concluído. De A fazer, o item pode ir para: Em andamento, Cancelado.")
    for nome in ("Em andamento", "Bloqueado", "Em andamento", "Em validação", "Concluído", "A fazer"):
        assert _mudar(c["membro"], item["chave"], c["status"][nome]).status_code == 200, nome


def test_adm_ajusta_o_fluxo(cenario):
    c = cenario
    wf = _wf(c["adm"])
    a_fazer, concluido = _id_status(wf, "A fazer"), _id_status(wf, "Concluído")
    novo = c["adm"].put("/api/espacos/LOP/transicoes", json={"pares": wf["transicoes"] + [[a_fazer, concluido]]})
    assert novo.status_code == 200
    item = criar_item(c["adm"], c)
    assert _mudar(c["adm"], item["chave"], concluido).status_code == 200
    assert c["membro"].put("/api/espacos/LOP/transicoes", json={"pares": []}).status_code == 403


def test_status_proprio_com_aviso_de_nome_parecido(cenario):
    c = cenario
    aviso = c["adm"].post("/api/espacos/LOP/status", json={"nome": "BLOCKED", "categoria": "em_andamento"})
    assert aviso.status_code == 409
    assert aviso.json()["detail"]["codigo"] == "status_parecido"
    assert "Bloqueado" in aviso.json()["detail"]["mensagem"]
    criado = c["adm"].post("/api/espacos/LOP/status", json={"nome": "Em revisão jurídica", "categoria": "em_andamento"})
    assert criado.status_code == 201
    proprio = next(s for s in criado.json()["ligados"] if s["nome"] == "Em revisão jurídica")
    assert proprio["proprio"] is True
    # O status próprio não aparece nos outros espaços.
    criar_projeto(c["adm"], sigla="SUP", nome="Suporte")
    assert "Em revisão jurídica" not in [s["nome"] for s in _wf(c["adm"], "SUP")["ligados"]]
    assert "Em revisão jurídica" not in [s["nome"] for s in _wf(c["adm"], "SUP")["disponiveis"]]
    # E ganhou coluna no quadro do espaço.
    [quadro] = c["adm"].get("/api/espacos/LOP/quadros").json()
    assert "Em revisão jurídica" in [col["nome"] for col in c["adm"].get(f"/api/quadros/{quadro['id']}").json()["colunas"]]


@pytest.mark.parametrize("novo,existente", [
    ("Bloqueado ", "Bloqueado"), ("bloqueado", "Bloqueado"), ("Blocked", "Bloqueado"), ("Em validacao", "Em validação"),
    ("Em valdação", "Em validação"), ("Done", "Concluído"), ("In Progress", "Em andamento"),
])
def test_nomes_parecidos(novo, existente):
    assert nome_parecido(novo, ["Bloqueado", "Em validação", "Concluído", "Em andamento"]) == existente


def test_nome_diferente_nao_avisa():
    assert nome_parecido("Em revisão jurídica", ["Bloqueado", "Em validação", "Concluído"]) is None


def test_status_em_uso_so_sai_depois_de_mover_os_itens(cenario):
    c = cenario
    item = criar_item(c["adm"], c)
    wf = _wf(c["adm"])
    em_uso = c["adm"].delete(f"/api/espacos/LOP/status/{_id_status(wf, 'A fazer')}")
    assert em_uso.json()["detail"] == "Há 1 item(ns) em A fazer. Mova os itens para outro status antes."
    # Status sem itens sai, e as transições e a coluna dele saem junto.
    bloqueado = _id_status(wf, "Bloqueado")
    depois = c["adm"].delete(f"/api/espacos/LOP/status/{bloqueado}").json()
    assert "Bloqueado" not in [s["nome"] for s in depois["ligados"]]
    assert "Bloqueado" in [s["nome"] for s in depois["disponiveis"]]
    assert all(bloqueado not in par for par in depois["transicoes"])
    assert _mudar(c["adm"], item["chave"], c["status"]["Em andamento"]).status_code == 200
    # Status padrão desligado pode ser religado.
    religado = c["adm"].post(f"/api/espacos/LOP/status/{bloqueado}/ligar").json()
    assert "Bloqueado" in [s["nome"] for s in religado["ligados"]]


def test_catalogo_padrao_e_promocao_so_pelo_adm_da_plataforma(cenario):
    c = cenario
    assert c["membro"].get("/api/admin/status").status_code == 403
    novo = c["adm"].post("/api/admin/status", json={"nome": "Em homologação", "categoria": "em_andamento"})
    assert novo.status_code == 201
    # Padrão novo fica disponível nos espaços, sem ser imposto.
    assert "Em homologação" in [s["nome"] for s in _wf(c["adm"])["disponiveis"]]
    assert "Em homologação" not in [s["nome"] for s in _wf(c["adm"])["ligados"]]
    proprio = c["adm"].post("/api/espacos/LOP/status", json={"nome": "Aguardando cliente", "categoria": "em_andamento"}).json()
    sid = next(s["id"] for s in proprio["ligados"] if s["nome"] == "Aguardando cliente")
    assert c["adm"].post(f"/api/admin/status/{sid}/promover").status_code == 200
    criar_projeto(c["adm"], sigla="SUP", nome="Suporte")
    assert "Aguardando cliente" in [s["nome"] for s in _wf(c["adm"], "SUP")["disponiveis"]]


# --- Quadros ----------------------------------------------------------------------------------

def _quadro(cliente, sigla="LOP"):
    [q] = [q for q in cliente.get(f"/api/espacos/{sigla}/quadros").json() if q["painel_id"] is None][:1]
    return cliente.get(f"/api/quadros/{q['id']}").json()


def test_kanban_nasce_com_uma_coluna_por_status_e_backlog_separado(cenario):
    c = cenario
    quadro = _quadro(c["adm"])
    assert quadro["tipo"] == "kanban" and quadro["usa_backlog"] is True
    assert [col["nome"] for col in quadro["colunas"]] == [
        "A fazer", "Em andamento", "Em validação", "Aguardando terceiros", "Bloqueado", "Concluído", "Cancelado"]
    criar_item(c["adm"], c, status_id=c["status"]["Backlog"], resumo="Ideia")
    criar_item(c["adm"], c, resumo="Tarefa do quadro")
    quadro = _quadro(c["adm"])
    assert [x["resumo"] for x in quadro["backlog"]] == ["Ideia"]
    assert [x["resumo"] for x in quadro["colunas"][0]["cards"]] == ["Tarefa do quadro"]


def test_desligar_backlog_vira_primeira_coluna(cenario):
    c = cenario
    quadro = _quadro(c["adm"])
    c["adm"].patch(f"/api/quadros/{quadro['id']}", json={"usa_backlog": False})
    quadro = _quadro(c["adm"])
    assert quadro["colunas"][0]["nome"] == "Backlog"
    c["adm"].patch(f"/api/quadros/{quadro['id']}", json={"usa_backlog": True})
    assert _quadro(c["adm"])["colunas"][0]["nome"] == "A fazer"


def test_modelos_definem_o_tipo_de_quadro(cliente_adm):
    criar_projeto(cliente_adm, sigla="GT", modelo="gestao_tarefas")
    simples = _quadro(cliente_adm, "GT")
    assert simples["tipo"] == "simples" and simples["usa_backlog"] is False
    assert simples["colunas"][0]["nome"] == "Backlog"


def test_colunas_juntam_status_e_limite_gera_alerta(cenario):
    c = cenario
    quadro = _quadro(c["adm"])
    st = {s["nome"]: s["id"] for col in quadro["colunas"] for s in col["status"]}
    colunas = [
        {"nome": "A fazer", "status_ids": [st["A fazer"]], "limite": 1},
        {"nome": "Fazendo", "status_ids": [st["Em andamento"], st["Aguardando terceiros"], st["Bloqueado"]]},
        {"nome": "Validando", "status_ids": [st["Em validação"]]},
        {"nome": "Fim", "status_ids": [st["Concluído"], st["Cancelado"]]},
    ]
    assert c["adm"].put(f"/api/quadros/{quadro['id']}/colunas", json={"colunas": colunas}).status_code == 204
    criar_item(c["adm"], c)
    criar_item(c["adm"], c)
    quadro = _quadro(c["adm"])
    assert [col["nome"] for col in quadro["colunas"]] == ["A fazer", "Fazendo", "Validando", "Fim"]
    assert quadro["colunas"][0]["acima_do_limite"] is True
    repetido = c["adm"].put(f"/api/quadros/{quadro['id']}/colunas", json={"colunas": colunas + [
        {"nome": "Outra", "status_ids": [st["A fazer"]]}]})
    assert repetido.json()["detail"] == "O status A fazer está em mais de uma coluna."
    assert c["membro"].put(f"/api/quadros/{quadro['id']}/colunas", json={"colunas": colunas}).status_code == 403


def test_card_mostra_bloqueio_e_atraso(cenario, relogio_falso):
    c = cenario
    a = criar_item(c["adm"], c, data_entrega="2026-11-17")
    b = criar_item(c["adm"], c, data_entrega="2026-11-17")
    c["adm"].post(f"/api/itens/{a['chave']}/vinculos", json={"tipo": "bloqueia", "chave": b["chave"]})
    cards = {x["chave"]: x for x in _quadro(c["adm"])["colunas"][0]["cards"]}
    assert cards[b["chave"]]["bloqueado"] is True
    assert cards[a["chave"]]["bloqueado"] is False


def test_destinos_do_fluxo_vem_com_o_quadro(cenario):
    c = cenario
    quadro = _quadro(c["adm"])
    destinos = quadro["destinos"][c["status"]["A fazer"]]
    assert set(destinos) == {c["status"]["Em andamento"], c["status"]["Cancelado"]}


def test_painel_tem_quadro_proprio_com_os_itens_dele(cenario):
    c = cenario
    painel = c["adm"].post("/api/espacos/LOP/paineis", json={"nome": "Suporte B2B"}).json()
    criar_item(c["adm"], c, painel_id=painel["id"], resumo="Do painel")
    quadros = c["adm"].get("/api/espacos/LOP/quadros").json()
    do_painel = next(q for q in quadros if q["painel_id"] == painel["id"])
    principal = next(q for q in quadros if q["painel_id"] is None)
    ver = c["adm"].get(f"/api/quadros/{do_painel['id']}").json()
    assert ver["nome"] == "Suporte B2B"
    assert [x["resumo"] for x in ver["colunas"][0]["cards"]] == ["Do painel"]
    assert c["adm"].delete(f"/api/quadros/{do_painel['id']}").json()["detail"] == "O quadro de um painel sai junto com o painel."
    assert c["adm"].delete(f"/api/quadros/{principal['id']}").json()["detail"] == "O espaço precisa de pelo menos um quadro."


def test_varios_quadros_no_mesmo_espaco(cenario):
    c = cenario
    novo = c["adm"].post("/api/espacos/LOP/quadros", json={"nome": "Sprint", "tipo": "simples"})
    assert novo.status_code == 201
    assert len([q for q in c["adm"].get("/api/espacos/LOP/quadros").json() if q["painel_id"] is None]) == 2
    assert c["adm"].delete(f"/api/quadros/{novo.json()['id']}").status_code == 204


def test_quadro_de_espaco_sem_acesso(cenario, novo_cliente):
    from conftest import entrar

    fora = novo_cliente()
    entrar(fora, "fora@jusbrasil.com.br", "Fora")
    quadro = _quadro(cenario["adm"])
    assert fora.get(f"/api/quadros/{quadro['id']}").status_code == 404


# --- Gantt ------------------------------------------------------------------------------------

def test_gantt_com_barras_hierarquia_e_setas_de_bloqueio(cenario):
    c = cenario
    epico = criar_item(c["adm"], c, tipo_id=c["tipos"]["Épico"], resumo="Épico", data_inicio="2026-11-10")
    a = criar_item(c["adm"], c, pai_id=epico["id"], data_inicio="2026-11-12", data_entrega="2026-11-20")
    b = criar_item(c["adm"], c, data_inicio="2026-11-21", data_entrega="2026-11-28")
    c["adm"].post(f"/api/itens/{a['chave']}/vinculos", json={"tipo": "bloqueia", "chave": b["chave"]})
    gantt = c["adm"].get("/api/espacos/LOP/gantt").json()
    assert [b_["chave"] for b_ in gantt["barras"]] == ["LOP-1", "LOP-2", "LOP-3"]
    assert gantt["barras"][1]["pai"] == "LOP-1"
    assert gantt["bloqueios"] == [["LOP-2", "LOP-3"]]
