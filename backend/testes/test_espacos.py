"""Espaços, membros, painéis, tipos próprios, origens e Times provisórios (Etapa 2)."""

from conftest import entrar, eventos


def _id(cliente) -> str:
    return cliente.get("/api/eu").json()["id"]


def criar_projeto(cliente, sigla="LOP", nome="Legal Ops", modelo="kanban"):
    resposta = cliente.post("/api/espacos", json={"tipo": "projeto", "nome": nome, "sigla": sigla, "modelo": modelo})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def test_quem_pode_criar_espaco_de_equipe_vira_adm(cliente_adm, db):
    espaco = criar_projeto(cliente_adm, sigla="lop")
    assert espaco["sigla"] == "LOP"
    assert espaco["meu_papel"] == "adm"
    assert espaco["modelo"] == "kanban"
    assert espaco["permissoes"]["gerenciar_membros"] is True
    assert [t["nome"] for t in espaco["tipos"]] == ["Épico", "História", "Tarefa", "Bug", "Subtarefa"]
    assert [s["nome"] for s in espaco["status"]][:3] == ["Backlog", "A fazer", "Em andamento"]
    assert len(espaco["status"]) == 8
    assert eventos(db, "espaco_criado")[0].detalhes["espaco"] == "LOP"


def test_usuario_comum_nao_cria_espaco_de_equipe_mas_cria_pessoal(cliente):
    entrar(cliente, "comum@jusbrasil.com.br", "Comum")
    negado = cliente.post("/api/espacos", json={"tipo": "projeto", "nome": "X", "sigla": "XX", "modelo": "kanban"})
    assert negado.status_code == 403
    pessoal = cliente.post("/api/espacos", json={"tipo": "pessoal", "nome": "Minhas tarefas", "sigla": "MEU"})
    assert pessoal.status_code == 201
    assert pessoal.json()["meu_papel"] == "dono"
    assert pessoal.json()["modelo"] is None
    assert [e["sigla"] for e in cliente.get("/api/espacos").json()] == ["MEU"]


def test_quem_tem_permissao_de_criar_espacos_cria(novo_cliente, cliente_adm):
    pessoa = novo_cliente()
    entrar(pessoa, "cria@jusbrasil.com.br", "Cria")
    cliente_adm.post(f"/api/admin/usuarios/{_id(pessoa)}/papeis", json={"papel": "criar_espacos"})
    assert criar_projeto(pessoa, sigla="TLF")["meu_papel"] == "adm"


def test_sigla_valida_unica_e_modelo_obrigatorio(cliente_adm):
    criar_projeto(cliente_adm, sigla="LOP")
    for sigla, mensagem in [
        ("L", "A sigla precisa ter de 2 a 10 letras, sem acentos, números ou espaços."),
        ("LOP1", "A sigla precisa ter de 2 a 10 letras, sem acentos, números ou espaços."),
        ("ÇAO", "A sigla precisa ter de 2 a 10 letras, sem acentos, números ou espaços."),
        ("lop", "A sigla LOP já é usada por outro espaço."),
    ]:
        r = cliente_adm.post("/api/espacos", json={"tipo": "projeto", "nome": "X", "sigla": sigla, "modelo": "scrum"})
        assert r.status_code == 409 and r.json()["detail"] == mensagem, (sigla, r.text)
    sem_modelo = cliente_adm.post("/api/espacos", json={"tipo": "projeto", "nome": "X", "sigla": "XY"})
    assert sem_modelo.json()["detail"] == "Escolha o modelo do espaço."


def test_espaco_privado_e_invisivel_para_quem_nao_e_membro(novo_cliente, cliente_adm):
    criar_projeto(cliente_adm)
    fora = novo_cliente()
    entrar(fora, "fora@jusbrasil.com.br", "Fora")
    assert fora.get("/api/espacos/LOP").status_code == 404
    assert fora.get("/api/espacos").json() == []


def test_membros_com_papeis_e_regras(novo_cliente, cliente_adm, db):
    criar_projeto(cliente_adm)
    membro, leitor = novo_cliente(), novo_cliente()
    entrar(membro, "membro@jusbrasil.com.br", "Membro")
    entrar(leitor, "leitor@jusbrasil.com.br", "Leitor")

    assert cliente_adm.post("/api/espacos/LOP/membros", json={"usuario_id": _id(membro), "papel": "membro"}).status_code == 204
    assert cliente_adm.post("/api/espacos/LOP/membros", json={"usuario_id": _id(leitor), "papel": "leitor"}).status_code == 204
    repetido = cliente_adm.post("/api/espacos/LOP/membros", json={"usuario_id": _id(leitor), "papel": "membro"})
    assert repetido.json()["detail"] == "Leitor já é Leitor deste espaço."

    detalhe = leitor.get("/api/espacos/LOP").json()
    assert detalhe["meu_papel"] == "leitor"
    assert detalhe["permissoes"]["criar_itens"] is False
    assert detalhe["permissoes"]["comentar"] is True
    # Membro não gerencia membros.
    assert membro.post("/api/espacos/LOP/membros", json={"usuario_id": _id(leitor), "papel": "adm"}).status_code == 403

    assert cliente_adm.patch(f"/api/espacos/LOP/membros/{_id(leitor)}", json={"papel": "membro"}).status_code == 204
    assert [m["papel"] for m in cliente_adm.get("/api/espacos/LOP/membros").json()] == ["adm", "membro", "membro"]
    assert cliente_adm.delete(f"/api/espacos/LOP/membros/{_id(leitor)}").status_code == 204
    assert leitor.get("/api/espacos/LOP").status_code == 404
    assert [e.tipo for e in eventos(db) if e.tipo.startswith("membro_")] == [
        "membro_adicionado", "membro_adicionado", "membro_papel_alterado", "membro_removido"]


def test_espaco_nunca_fica_sem_adm(cliente_adm, adm):
    criar_projeto(cliente_adm)
    r = cliente_adm.patch(f"/api/espacos/LOP/membros/{adm.id}", json={"papel": "membro"})
    assert r.json()["detail"] == "O espaço precisa ter pelo menos um ADM."
    assert cliente_adm.delete(f"/api/espacos/LOP/membros/{adm.id}").json()["detail"] == "O espaço precisa ter pelo menos um ADM."


def test_espaco_pessoal_nao_tem_membros_nem_paineis(cliente):
    entrar(cliente, "p@jusbrasil.com.br", "P")
    cliente.post("/api/espacos", json={"tipo": "pessoal", "nome": "Meu", "sigla": "MEU"})
    r = cliente.post("/api/espacos/MEU/membros", json={"usuario_id": _id(cliente), "papel": "membro"})
    assert r.status_code == 409
    assert cliente.post("/api/espacos/MEU/paineis", json={"nome": "X"}).status_code == 409


def test_paineis_tipos_e_origens(cliente_adm):
    criar_projeto(cliente_adm)
    painel = cliente_adm.post("/api/espacos/LOP/paineis", json={"nome": "Suporte B2B"}).json()
    assert cliente_adm.post("/api/espacos/LOP/paineis", json={"nome": "Suporte B2B"}).status_code == 409
    assert cliente_adm.patch(f"/api/espacos/LOP/paineis/{painel['id']}", json={"nome": "Suporte"}).status_code == 204

    tipo = cliente_adm.post("/api/espacos/LOP/tipos", json={"nome": "Processo"}).json()
    assert tipo["nivel"] == "padrao"
    assert cliente_adm.post("/api/espacos/LOP/tipos", json={"nome": "tarefa"}).json()["detail"] == "Já existe um tipo chamado tarefa."
    padrao = next(t for t in cliente_adm.get("/api/espacos/LOP").json()["tipos"] if t["nome"] == "Bug")
    assert cliente_adm.delete(f"/api/espacos/LOP/tipos/{padrao['id']}").json()["detail"] == (
        "Os tipos padrão da plataforma não podem ser alterados.")

    origem = cliente_adm.post("/api/espacos/LOP/origens", json={"nome": "Slack"}).json()
    detalhe = cliente_adm.get("/api/espacos/LOP").json()
    assert [p["nome"] for p in detalhe["paineis"]] == ["Suporte"]
    assert "Processo" in [t["nome"] for t in detalhe["tipos"]]
    assert [o["nome"] for o in detalhe["origens"]] == ["Slack"]
    assert cliente_adm.delete(f"/api/espacos/LOP/origens/{origem['id']}").status_code == 204
    assert cliente_adm.get("/api/espacos/LOP").json()["origens"] == []
    # Reativar ao recriar com o mesmo nome.
    assert cliente_adm.post("/api/espacos/LOP/origens", json={"nome": "Slack"}).json()["id"] == origem["id"]


def test_times_provisorios_so_adm_da_plataforma_mantem(novo_cliente, cliente_adm):
    comum = novo_cliente()
    entrar(comum, "c@jusbrasil.com.br", "C")
    assert comum.post("/api/admin/times", json={"nome": "Legal Ops"}).status_code == 403

    time = cliente_adm.post("/api/admin/times", json={"nome": "Legal Ops"}).json()
    assert cliente_adm.post("/api/admin/times", json={"nome": "legal ops"}).json()["detail"] == (
        "Já existe um time chamado Legal Ops.")
    assert [t["nome"] for t in comum.get("/api/times").json()] == ["Legal Ops"]
    cliente_adm.patch(f"/api/admin/times/{time['id']}", json={"ativo": False})
    assert comum.get("/api/times").json() == []
    assert len(cliente_adm.get("/api/times", params={"todos": True}).json()) == 1


def test_busca_de_pessoas(novo_cliente, cliente_adm):
    entrar(novo_cliente(), "bruno.reis@jusbrasil.com.br", "Bruno Reis")
    assert [p["nome"] for p in cliente_adm.get("/api/pessoas", params={"busca": "brun"}).json()] == ["Bruno Reis"]
