"""Etapa 3b: sprints, backlog do Scrum, estimativa, burndown, velocidade, relatório, fluxo acumulado e tempo de ciclo."""

import pytest
from conftest import criar_item, criar_projeto, entrar


@pytest.fixture
def scrum(novo_cliente, cliente_adm):
    """Espaço Scrum SCR com um Membro e um Leitor; devolve o necessário para os testes."""
    espaco = criar_projeto(cliente_adm, sigla="SCR", nome="Time Scrum", modelo="scrum")
    time = cliente_adm.post("/api/admin/times", json={"nome": "Legal Ops"}).json()
    membro, leitor = novo_cliente(), novo_cliente()
    entrar(membro, "membro@jusbrasil.com.br", "Marta Membro")
    entrar(leitor, "leitor@jusbrasil.com.br", "Leo Leitor")
    ids = {}
    for cliente, papel in ((membro, "membro"), (leitor, "leitor")):
        ids[papel] = cliente.get("/api/eu").json()["id"]
        cliente_adm.post("/api/espacos/SCR/membros", json={"usuario_id": ids[papel], "papel": papel})
    [quadro] = cliente_adm.get("/api/espacos/SCR/quadros").json()
    c = {"adm": cliente_adm, "membro": membro, "leitor": leitor, "time": time["id"], "membro_id": ids["membro"],
         "tipos": {t["nome"]: t["id"] for t in espaco["tipos"]}, "status": {s["nome"]: s["id"] for s in espaco["status"]},
         "quadro": quadro["id"]}
    return c


def item(c, **extra):
    return criar_item(c["adm"], c, sigla="SCR", status_id=c["status"]["Backlog"], **extra)


def sprint(c, cliente=None, **dados):
    r = (cliente or c["membro"]).post(f"/api/quadros/{c['quadro']}/sprints", json=dados)
    assert r.status_code == 201, r.text
    return r.json()


def planejamento(c):
    return c["adm"].get(f"/api/quadros/{c['quadro']}/planejamento").json()


def mudar(c, chave, nome):
    r = c["adm"].patch(f"/api/itens/{chave}", json={"dados": {"status_id": c["status"][nome]}})
    assert r.status_code == 200, r.text


def test_quadro_scrum_nasce_com_backlog_e_unidade_em_pontos(scrum):
    c = scrum
    [quadro] = c["adm"].get("/api/espacos/SCR/quadros").json()
    assert quadro["tipo"] == "scrum" and quadro["unidade_estimativa"] == "pontos"
    item(c, resumo="Ideia", estimativa=3)
    p = planejamento(c)
    assert [x["resumo"] for x in p["backlog"]] == ["Ideia"]
    assert p["backlog_total"] == "3.00" or float(p["backlog_total"]) == 3
    assert p["nome_unidade"] == "Story points"


def test_membro_cria_sprint_e_leitor_nao(scrum):
    c = scrum
    s = sprint(c, objetivo="Fechar o fluxo de prazos")
    assert s["nome"] == "Sprint 1" and s["estado"] == "planejada"
    assert sprint(c)["nome"] == "Sprint 2"
    negado = c["leitor"].post(f"/api/quadros/{c['quadro']}/sprints", json={})
    assert negado.status_code == 403


def test_item_entra_na_sprint_e_sai_do_backlog_para_a_fazer(scrum):
    c = scrum
    i = item(c)
    s = sprint(c)
    assert c["membro"].post(f"/api/sprints/{s['id']}/itens", json={"chave": i["chave"]}).status_code == 204
    assert c["adm"].get(f"/api/itens/{i['chave']}").json()["status"]["nome"] == "A fazer"
    p = planejamento(c)
    assert p["backlog"] == []
    assert [x["chave"] for x in p["sprints"][0]["itens"]] == [i["chave"]]
    # Voltar ao backlog não muda o status.
    assert c["membro"].delete(f"/api/sprints/{s['id']}/itens/{i['chave']}").status_code == 204
    assert c["adm"].get(f"/api/itens/{i['chave']}").json()["status"]["nome"] == "A fazer"
    assert [x["chave"] for x in planejamento(c)["backlog"]] == [i["chave"]]


def test_item_so_fica_em_uma_sprint_aberta(scrum):
    c = scrum
    i = item(c)
    s1, s2 = sprint(c), sprint(c)
    c["membro"].post(f"/api/sprints/{s1['id']}/itens", json={"chave": i["chave"]})
    r = c["membro"].post(f"/api/sprints/{s2['id']}/itens", json={"chave": i["chave"]})
    assert r.json()["detail"] == f"{i['chave']} já está na Sprint 1. Tire de lá antes."


def test_varias_sprints_ativas_no_mesmo_quadro(scrum):
    c = scrum
    for s in (sprint(c), sprint(c)):
        r = c["membro"].post(f"/api/sprints/{s['id']}/iniciar", json={"inicio": "2026-11-16", "fim": "2026-11-27"})
        assert r.status_code == 200 and r.json()["estado"] == "ativa"
    assert [s["estado"] for s in planejamento(c)["sprints"]] == ["ativa", "ativa"]


def test_iniciar_exige_fim_e_fotografa_o_compromisso(scrum):
    c = scrum
    s = sprint(c)
    for pontos in (3, 5):
        i = item(c, estimativa=pontos)
        c["membro"].post(f"/api/sprints/{s['id']}/itens", json={"chave": i["chave"]})
    sem_fim = c["membro"].post(f"/api/sprints/{s['id']}/iniciar", json={})
    assert sem_fim.json()["detail"] == "Defina a data de fim da sprint."
    ativa = c["membro"].post(f"/api/sprints/{s['id']}/iniciar", json={"inicio": "2026-11-16", "fim": "2026-11-27"}).json()
    assert float(ativa["compromisso"]) == 8


def test_estimativa_por_horas_ou_contagem(scrum):
    c = scrum
    i = item(c, estimativa=13, estimativa_horas=6)
    assert float(c["adm"].get(f"/api/itens/{i['chave']}").json()["estimativa_horas"]) == 6
    assert c["leitor"].put(f"/api/quadros/{c['quadro']}/unidade", json={"unidade": "horas"}).status_code == 403
    c["adm"].put(f"/api/quadros/{c['quadro']}/unidade", json={"unidade": "horas"})
    assert float(planejamento(c)["backlog_total"]) == 6
    c["adm"].put(f"/api/quadros/{c['quadro']}/unidade", json={"unidade": "itens"})
    assert float(planejamento(c)["backlog_total"]) == 1


def test_encerrar_manda_abertos_para_onde_a_pessoa_escolher(scrum):
    c = scrum
    s1 = sprint(c)
    feito, aberto = item(c, estimativa=5), item(c, estimativa=3)
    for i in (feito, aberto):
        c["membro"].post(f"/api/sprints/{s1['id']}/itens", json={"chave": i["chave"]})
    c["membro"].post(f"/api/sprints/{s1['id']}/iniciar", json={"inicio": "2026-11-16", "fim": "2026-11-27"})
    for nome in ("Em andamento", "Em validação", "Concluído"):
        mudar(c, feito["chave"], nome)
    rel = c["membro"].post(f"/api/sprints/{s1['id']}/encerrar", json={"destino": "nova"}).json()
    assert [x["chave"] for x in rel["concluidos"]] == [feito["chave"]]
    assert [x["chave"] for x in rel["nao_concluidos"]] == [aberto["chave"]]
    assert float(rel["sprint"]["entregue"]) == 5
    p = planejamento(c)
    assert [s["nome"] for s in p["sprints"]] == ["Sprint 2"]
    assert [x["chave"] for x in p["sprints"][0]["itens"]] == [aberto["chave"]]


def test_encerrar_devolvendo_ao_backlog(scrum):
    c = scrum
    s = sprint(c)
    aberto = item(c)
    c["membro"].post(f"/api/sprints/{s['id']}/itens", json={"chave": aberto["chave"]})
    c["membro"].post(f"/api/sprints/{s['id']}/iniciar", json={"inicio": "2026-11-16", "fim": "2026-11-27"})
    c["membro"].post(f"/api/sprints/{s['id']}/encerrar", json={"destino": "backlog"})
    assert [x["chave"] for x in planejamento(c)["backlog"]] == [aberto["chave"]]
    destino_ruim = sprint(c)
    c["membro"].post(f"/api/sprints/{destino_ruim['id']}/iniciar", json={"inicio": "2026-11-16", "fim": "2026-11-27"})
    c["membro"].post(f"/api/sprints/{destino_ruim['id']}/encerrar", json={"destino": "backlog"})
    outra = sprint(c)
    c["membro"].post(f"/api/sprints/{outra['id']}/iniciar", json={"fim": "2026-11-30"})
    r = c["membro"].post(f"/api/sprints/{outra['id']}/encerrar", json={"destino": destino_ruim["id"]})
    assert r.json()["detail"] == "Escolha uma sprint aberta deste quadro."


def test_so_sprint_planejada_pode_ser_excluida(scrum):
    c = scrum
    s = sprint(c)
    i = item(c)
    c["membro"].post(f"/api/sprints/{s['id']}/itens", json={"chave": i["chave"]})
    assert c["membro"].delete(f"/api/sprints/{s['id']}").status_code == 204
    assert [x["chave"] for x in planejamento(c)["backlog"]] == [i["chave"]]
    ativa = sprint(c)
    c["membro"].post(f"/api/sprints/{ativa['id']}/iniciar", json={"fim": "2026-11-30"})
    assert c["membro"].delete(f"/api/sprints/{ativa['id']}").json()["detail"] == (
        "Só sprints que ainda não começaram podem ser excluídas.")


def test_sprint_nao_existe_em_quadro_kanban(cliente_adm):
    criar_projeto(cliente_adm, sigla="KB", modelo="kanban")
    [q] = cliente_adm.get("/api/espacos/KB/quadros").json()
    assert cliente_adm.post(f"/api/quadros/{q['id']}/sprints", json={}).json()["detail"] == "Sprints só existem em quadros Scrum."


# --- Métricas ---------------------------------------------------------------------------------

def test_burndown_com_escopo_adicionado_e_linha_ideal(scrum, relogio_falso):
    c = scrum
    s = sprint(c)
    a, b = item(c, estimativa=5), item(c, estimativa=5)
    for i in (a, b):
        c["membro"].post(f"/api/sprints/{s['id']}/itens", json={"chave": i["chave"]})
    c["membro"].post(f"/api/sprints/{s['id']}/iniciar", json={"inicio": "2026-11-16", "fim": "2026-11-20"})
    relogio_falso.avancar(days=1)
    for nome in ("Em andamento", "Em validação", "Concluído"):
        mudar(c, a["chave"], nome)
    relogio_falso.avancar(days=1)
    extra = item(c, estimativa=2)
    c["membro"].post(f"/api/sprints/{s['id']}/itens", json={"chave": extra["chave"]})
    pontos = c["adm"].get(f"/api/sprints/{s['id']}/burndown").json()
    assert [p["dia"] for p in pontos] == ["2026-11-16", "2026-11-17", "2026-11-18", "2026-11-19", "2026-11-20"]
    assert [None if p["restante"] is None else float(p["restante"]) for p in pontos] == [10, 5, 7, None, None]
    assert [float(p["ideal"]) for p in pontos] == [10, 7.5, 5, 2.5, 0]
    rel = c["adm"].get(f"/api/sprints/{s['id']}/relatorio").json()
    assert [x["chave"] for x in rel["adicionados_depois"]] == [extra["chave"]]


def test_velocidade_das_sprints_encerradas(scrum):
    c = scrum
    for pontos in (8, 5):
        s = sprint(c)
        i = item(c, estimativa=pontos)
        c["membro"].post(f"/api/sprints/{s['id']}/itens", json={"chave": i["chave"]})
        c["membro"].post(f"/api/sprints/{s['id']}/iniciar", json={"fim": "2026-11-30"})
        for nome in ("Em andamento", "Em validação", "Concluído"):
            mudar(c, i["chave"], nome)
        c["membro"].post(f"/api/sprints/{s['id']}/encerrar", json={"destino": "backlog"})
    v = c["adm"].get(f"/api/quadros/{c['quadro']}/velocidade").json()
    assert [(x["sprint"], float(x["compromisso"]), float(x["entregue"])) for x in v] == [("Sprint 1", 8, 8), ("Sprint 2", 5, 5)]


def test_fluxo_acumulado_e_tempo_de_ciclo(cenario, relogio_falso):
    c = cenario
    a = criar_item(c["adm"], c)
    relogio_falso.avancar(days=1)
    c["adm"].patch(f"/api/itens/{a['chave']}", json={"dados": {"status_id": c["status"]["Em andamento"]}})
    relogio_falso.avancar(days=2, hours=12)
    for nome in ("Em validação", "Concluído"):
        c["adm"].patch(f"/api/itens/{a['chave']}", json={"dados": {"status_id": c["status"][nome]}})
    criar_item(c["adm"], c)
    [quadro] = [q for q in c["adm"].get("/api/espacos/LOP/quadros").json() if q["painel_id"] is None]
    fluxo = c["adm"].get(f"/api/quadros/{quadro['id']}/fluxo-acumulado", params={"dias": 7}).json()
    ultimo = fluxo[-1]
    assert (ultimo["a_fazer"], ultimo["em_andamento"], ultimo["concluido"]) == (1, 0, 1)
    dia_17 = next(d for d in fluxo if d["dia"] == "2026-11-17")
    assert (dia_17["a_fazer"], dia_17["em_andamento"], dia_17["concluido"]) == (0, 1, 0)
    ciclo = c["adm"].get(f"/api/quadros/{quadro['id']}/tempo-de-ciclo").json()
    assert [(x["chave"], x["dias"]) for x in ciclo["itens"]] == [(a["chave"], 2.5)]
    assert ciclo["media"] == 2.5 and ciclo["p85"] == 2.5


def test_quadro_da_sprint_mostra_so_os_itens_dela(scrum):
    c = scrum
    s = sprint(c)
    dentro, fora = item(c, resumo="Dentro"), item(c, resumo="Fora")
    c["membro"].post(f"/api/sprints/{s['id']}/itens", json={"chave": dentro["chave"]})
    q = c["adm"].get(f"/api/quadros/{c['quadro']}", params={"sprint_id": s["id"]}).json()
    assert [x["resumo"] for col in q["colunas"] for x in col["cards"]] == ["Dentro"]
    assert q["backlog"] == []
    assert fora
