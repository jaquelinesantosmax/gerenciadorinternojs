"""Itens: campos obrigatórios, hierarquia, histórico, exclusão, clonagem e campos personalizados."""

import pytest
from conftest import entrar, eventos
from test_espacos import criar_projeto


def _id(cliente) -> str:
    return cliente.get("/api/eu").json()["id"]


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


def test_cria_item_com_chave_sequencial_e_relator_automatico(cenario):
    c = cenario
    primeiro = criar_item(c["membro"], c)
    segundo = criar_item(c["adm"], c, resumo="Outro")
    assert (primeiro["chave"], segundo["chave"]) == ("LOP-1", "LOP-2")
    assert primeiro["relator"]["nome"] == "Marta Membro"
    assert primeiro["prioridade"] == "alta"
    assert primeiro["status"]["nome"] == "A fazer"
    assert c["leitor"].get("/api/itens/lop-1").json()["resumo"] == "Revisar fluxo de prazos"


@pytest.mark.parametrize("campo,mensagem", [
    ("resumo", "Informe o resumo."),
    ("tipo_id", "Informe o tipo."),
    ("status_id", "Informe o status."),
    ("prioridade", "Informe a prioridade."),
    ("responsavel_id", "Informe o responsável."),
    ("time_id", "Informe o time."),
    ("data_inicio", "Informe a data de início."),
    ("data_entrega", "Informe a data de entrega."),
])
def test_campos_obrigatorios(cenario, campo, mensagem):
    c = cenario
    dados = dados_item(c)
    dados.pop(campo)
    r = c["adm"].post("/api/espacos/LOP/itens", json={"dados": dados})
    assert r.status_code == 400 and r.json()["detail"] == mensagem


def test_regras_dos_campos_padrao(cenario):
    c = cenario
    def erro(**extra):
        return c["adm"].post("/api/espacos/LOP/itens", json={"dados": dados_item(c, **extra)}).json()["detail"]

    assert erro(prioridade="highest") == "Prioridade inválida."
    assert erro(responsavel_id=c["leitor_id"]) == "O responsável precisa ser ADM ou Membro do espaço."
    assert erro(data_entrega="2026-11-01") == "A data de entrega não pode ser antes da data de início."
    assert erro(data_real_entrega="2026-12-05") == (
        "A entrega real passou da data de entrega: informe a justificativa do atraso.")
    ok = c["adm"].post("/api/espacos/LOP/itens", json={"dados": dados_item(
        c, data_real_entrega="2026-12-05", justificativa_atraso="Cliente atrasou o envio")})
    assert ok.status_code == 201
    assert erro(estimativa=-1) == "Estimativa: valor inválido."
    assert erro(campo_inventado=1) == "Campo desconhecido: campo_inventado"


def test_painel_obrigatorio_quando_o_espaco_tem_paineis(cenario):
    c = cenario
    painel = c["adm"].post("/api/espacos/LOP/paineis", json={"nome": "Suporte B2B"}).json()
    sem = c["adm"].post("/api/espacos/LOP/itens", json={"dados": dados_item(c)})
    assert sem.json()["detail"] == "Informe o painel."
    item = criar_item(c["adm"], c, painel_id=painel["id"])
    assert item["painel"]["nome"] == "Suporte B2B"
    em_uso = c["adm"].delete(f"/api/espacos/LOP/paineis/{painel['id']}")
    assert em_uso.json()["detail"] == "O painel Suporte B2B tem 1 item(ns). Mova os itens antes de excluir."


def test_leitor_nao_cria_nem_edita(cenario):
    c = cenario
    item = criar_item(c["adm"], c)
    assert c["leitor"].post("/api/espacos/LOP/itens", json={"dados": dados_item(c)}).status_code == 403
    assert c["leitor"].patch(f"/api/itens/{item['chave']}", json={"dados": {"resumo": "x"}}).status_code == 403


def test_hierarquia_epico_tarefa_subtarefa(cenario):
    c = cenario
    epico = criar_item(c["adm"], c, tipo_id=c["tipos"]["Épico"], resumo="Automação de prazos")
    tarefa = criar_item(c["adm"], c, pai_id=epico["id"])
    sub = criar_item(c["adm"], c, tipo_id=c["tipos"]["Subtarefa"], resumo="Mapear", pai_id=tarefa["id"])
    assert sub["pai"]["chave"] == tarefa["chave"]
    assert [f["chave"] for f in c["adm"].get(f"/api/itens/{epico['chave']}").json()["filhos"]] == [tarefa["chave"]]

    def erro(**extra):
        return c["adm"].post("/api/espacos/LOP/itens", json={"dados": dados_item(c, **extra)}).json()["detail"]

    assert erro(tipo_id=c["tipos"]["Subtarefa"]) == "Uma Subtarefa precisa de um item pai."
    assert erro(tipo_id=c["tipos"]["Épico"], pai_id=epico["id"]) == "Um Épico não pode ter pai."
    assert erro(pai_id=tarefa["id"]) == "O pai de uma História, Tarefa ou Bug precisa ser um Épico."
    excluir = c["adm"].delete(f"/api/itens/{epico['chave']}")
    assert excluir.json()["detail"] == "Este item tem itens filhos. Exclua ou mova os filhos antes."


def test_tipo_proprio_fica_no_nivel_de_tarefa(cenario):
    c = cenario
    processo = c["adm"].post("/api/espacos/LOP/tipos", json={"nome": "Processo"}).json()
    epico = criar_item(c["adm"], c, tipo_id=c["tipos"]["Épico"])
    item = criar_item(c["adm"], c, tipo_id=processo["id"], pai_id=epico["id"])
    assert item["tipo"]["nome"] == "Processo" and item["nivel"] == "padrao"
    em_uso = c["adm"].delete(f"/api/espacos/LOP/tipos/{processo['id']}")
    assert em_uso.json()["detail"] == "Há 1 item(ns) do tipo Processo. Mude o tipo deles antes de excluir."


def test_edicao_gera_historico_com_valor_anterior_e_novo(cenario):
    c = cenario
    item = criar_item(c["adm"], c)
    r = c["membro"].patch(f"/api/itens/{item['chave']}", json={"dados": {
        "status_id": c["status"]["Em andamento"], "prioridade": "critica", "categorias": ["prazos", "TLF", "Prazos"],
    }})
    assert r.status_code == 200, r.text
    assert r.json()["categorias"] == ["prazos", "TLF"]
    historico = c["adm"].get(f"/api/itens/{item['chave']}/atividade", params={"filtro": "historico"}).json()
    mudancas = {h["campo"]: (h["valor_anterior"], h["valor_novo"]) for h in historico}
    assert mudancas["Status"] == ("A fazer", "Em andamento")
    assert mudancas["Prioridade"] == ("Alta", "Crítica")
    assert mudancas["Categorias"] == (None, "prazos, TLF")
    assert historico[0]["autor"]["nome"] == "Marta Membro"
    assert historico[-1]["campo"] == "criado"
    assert c["adm"].get("/api/espacos/LOP/opcoes-item").json()["categorias"] == ["prazos", "TLF"]


def test_excluir_proprio_item_e_de_outros(cenario, db):
    c = cenario
    meu = criar_item(c["membro"], c)
    do_adm = criar_item(c["adm"], c)
    assert c["membro"].delete(f"/api/itens/{do_adm['chave']}").status_code == 403
    assert c["membro"].delete(f"/api/itens/{meu['chave']}").status_code == 204
    assert c["adm"].get(f"/api/itens/{meu['chave']}").status_code == 404
    assert c["adm"].delete(f"/api/itens/{do_adm['chave']}").status_code == 204
    assert [e.detalhes["item"] for e in eventos(db, "item_excluido")] == ["LOP-1", "LOP-2"]


def test_clonar_cria_copia_com_vinculo_clona(cenario):
    c = cenario
    original = criar_item(c["adm"], c, categorias=["x"])
    copia = c["membro"].post(f"/api/itens/{original['chave']}/clonar").json()
    assert copia["chave"] == "LOP-2"
    assert copia["resumo"] == original["resumo"] and copia["categorias"] == ["x"]
    assert copia["relator"]["nome"] == "Marta Membro"
    assert [(v["rotulo"], v["chave"]) for v in copia["vinculos"]] == [("clona", "LOP-1")]
    assert [(v["rotulo"], v["chave"]) for v in c["adm"].get("/api/itens/LOP-1").json()["vinculos"]] == [
        ("é clonado de", "LOP-2")]


def test_campos_personalizados_por_tipo_e_obrigatorios(cenario):
    c = cenario
    adm = c["adm"]
    lista = adm.post("/api/espacos/LOP/campos", json={
        "nome": "Tribunal", "tipo": "lista_unica", "obrigatorio": True, "tipos_item": [c["tipos"]["Bug"]],
        "config": {"opcoes": [{"nome": "TJSP"}, {"nome": "TJRJ"}]}}).json()
    valor = adm.post("/api/espacos/LOP/campos", json={
        "nome": "Valor da causa", "tipo": "moeda", "tipos_item": [c["tipos"]["Bug"], c["tipos"]["Tarefa"]],
        "config": {"moeda": "BRL"}}).json()
    cascata = adm.post("/api/espacos/LOP/campos", json={
        "nome": "Área", "tipo": "lista_cascata", "tipos_item": [c["tipos"]["Tarefa"]],
        "config": {"opcoes": [{"nome": "Cível", "filhos": [{"nome": "Família"}, {"nome": "Consumidor"}]}]}}).json()
    assert adm.post("/api/espacos/LOP/campos", json={"nome": "X", "tipo": "moeda", "tipos_item": [c["tipos"]["Bug"]]}
                    ).json()["detail"] == "Escolha a moeda do campo."
    assert c["membro"].post("/api/espacos/LOP/campos", json={
        "nome": "Y", "tipo": "texto_curto", "tipos_item": [c["tipos"]["Bug"]]}).status_code == 403

    # Campo obrigatório só vale para Bug: a Tarefa entra sem ele.
    tarefa = criar_item(adm, c, valores={valor["id"]: "1500.5", cascata["id"]: {
        "pai": cascata["config"]["opcoes"][0]["id"], "filho": cascata["config"]["opcoes"][0]["filhos"][1]["id"]}})
    assert tarefa["valores"][valor["id"]] == "1500.50"
    sem = adm.post("/api/espacos/LOP/itens", json={"dados": dados_item(c, tipo_id=c["tipos"]["Bug"])})
    assert sem.json()["detail"] == "Informe Tribunal."
    errado = adm.post("/api/espacos/LOP/itens", json={"dados": dados_item(c, valores={lista["id"]: "TJMG"})})
    assert errado.json()["detail"] == "Campo personalizado inválido para este tipo."
    bug = criar_item(adm, c, tipo_id=c["tipos"]["Bug"], valores={lista["id"]: lista["config"]["opcoes"][0]["id"]})
    historico = adm.patch(f"/api/itens/{bug['chave']}", json={"dados": {"valores": {
        lista["id"]: lista["config"]["opcoes"][1]["id"]}}})
    assert historico.status_code == 200
    mudancas = adm.get(f"/api/itens/{bug['chave']}/atividade", params={"filtro": "historico"}).json()
    assert (mudancas[0]["campo"], mudancas[0]["valor_anterior"], mudancas[0]["valor_novo"]) == ("Tribunal", "TJSP", "TJRJ")


@pytest.mark.parametrize("tipo,config,valor,guardado", [
    ("texto_curto", {}, "  abc ", "abc"),
    ("texto_longo", {}, "linha 1\nlinha 2", "linha 1\nlinha 2"),
    ("numero", {}, "12.50", 12.5),
    ("numero", {}, 7, 7),
    ("data", {}, "2026-12-01", "2026-12-01"),
    ("data_hora", {}, "2026-12-01T10:00:00-03:00", "2026-12-01T10:00:00-03:00"),
    ("url", {}, "https://github.com/x", "https://github.com/x"),
    ("sim_nao", {}, True, True),
])
def test_tipos_de_campo_simples(cenario, tipo, config, valor, guardado):
    c = cenario
    campo = c["adm"].post("/api/espacos/LOP/campos", json={
        "nome": "Campo", "tipo": tipo, "tipos_item": [c["tipos"]["Tarefa"]], "config": config}).json()
    item = criar_item(c["adm"], c, valores={campo["id"]: valor})
    assert item["valores"][campo["id"]] == guardado


@pytest.mark.parametrize("tipo,valor,mensagem", [
    ("numero", "abc", "Campo: valor inválido."),
    ("url", "ftp://x", "Campo: o endereço precisa começar com http:// ou https://."),
    ("url", "javascript:alert(1)", "Campo: o endereço precisa começar com http:// ou https://."),
    ("data_hora", "2026-12-01T10:00:00", "Campo: informe o fuso horário."),
    ("sim_nao", "sim", "Campo: valor inválido."),
])
def test_valores_invalidos(cenario, tipo, valor, mensagem):
    c = cenario
    campo = c["adm"].post("/api/espacos/LOP/campos", json={
        "nome": "Campo", "tipo": tipo, "tipos_item": [c["tipos"]["Tarefa"]]}).json()
    r = c["adm"].post("/api/espacos/LOP/itens", json={"dados": dados_item(c, valores={campo["id"]: valor})})
    assert r.json()["detail"] == mensagem


def test_campo_pessoa_aceita_so_membros(cenario, novo_cliente):
    c = cenario
    fora = novo_cliente()
    entrar(fora, "fora@jusbrasil.com.br", "Fora")
    campo = c["adm"].post("/api/espacos/LOP/campos", json={
        "nome": "Revisores", "tipo": "pessoa", "tipos_item": [c["tipos"]["Tarefa"]], "config": {"varias": True}}).json()
    item = criar_item(c["adm"], c, valores={campo["id"]: [c["leitor_id"], c["membro_id"]]})
    assert item["valores"][campo["id"]] == [c["leitor_id"], c["membro_id"]]
    r = c["adm"].post("/api/espacos/LOP/itens", json={"dados": dados_item(c, valores={campo["id"]: [_id(fora)]})})
    assert r.json()["detail"] == "Revisores: escolha pessoas que são membros do espaço."


def test_opcao_desativada_continua_nos_itens_que_ja_a_usam(cenario):
    c = cenario
    campo = c["adm"].post("/api/espacos/LOP/campos", json={
        "nome": "Fase", "tipo": "lista_unica", "tipos_item": [c["tipos"]["Tarefa"]],
        "config": {"opcoes": [{"nome": "Inicial"}, {"nome": "Recursal"}]}}).json()
    inicial, recursal = campo["config"]["opcoes"]
    item = criar_item(c["adm"], c, valores={campo["id"]: inicial["id"]})
    # O ADM tira "Inicial" da lista.
    c["adm"].patch(f"/api/espacos/LOP/campos/{campo['id']}", json={"config": {"opcoes": [recursal]}})
    assert c["adm"].patch(f"/api/itens/{item['chave']}", json={"dados": {"resumo": "Mudou"}}).status_code == 200
    novo = c["adm"].post("/api/espacos/LOP/itens", json={"dados": dados_item(c, valores={campo["id"]: inicial["id"]})})
    assert novo.json()["detail"] == "Essa opção não está mais disponível."


def test_espaco_pessoal_so_o_dono_e_responsavel(cliente_adm, novo_cliente, cenario):
    c = cenario
    dono = novo_cliente()
    entrar(dono, "dono@jusbrasil.com.br", "Dona")
    dono.post("/api/espacos", json={"tipo": "pessoal", "nome": "Minhas", "sigla": "DONA"})
    item = criar_item(dono, c, sigla="DONA", responsavel_id=_id(dono))
    assert item["chave"] == "DONA-1"
    assert cliente_adm.get("/api/itens/DONA-1").status_code == 404
    r = dono.post("/api/espacos/DONA/itens", json={"dados": dados_item(c, responsavel_id=c["membro_id"])})
    assert r.json()["detail"] == "O responsável precisa ser ADM ou Membro do espaço."
