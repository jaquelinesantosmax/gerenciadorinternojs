"""Detalhe do item: texto formatado, comentários, atividade, anexos e itens relacionados."""

import io

import pytest
from conftest import criar_item, criar_projeto, entrar, eventos

from gerenciador import anexos as anexos_svc
from gerenciador.erros import ErroDeRegra
from gerenciador.texto_rico import mencoes, texto_simples, validar


def doc(*paragrafos, marcas=None):
    conteudo = [{"type": "paragraph", "content": [{"type": "text", "text": p, **({"marks": marcas} if marcas else {})}]}
                for p in paragrafos]
    return {"type": "doc", "content": conteudo}


# --- Texto formatado --------------------------------------------------------------------------

def test_texto_formatado_aceita_o_editor_e_extrai_mencoes():
    documento = {"type": "doc", "content": [
        {"type": "heading", "attrs": {"level": 2}, "content": [{"type": "text", "text": "Contexto"}]},
        {"type": "bulletList", "content": [{"type": "listItem", "content": [
            {"type": "paragraph", "content": [
                {"type": "text", "text": "ver ", "marks": [{"type": "bold"}]},
                {"type": "mention", "attrs": {"id": "7d1c3c55-1111-4111-8111-111111111111", "label": "Ana"}},
                {"type": "text", "text": " link", "marks": [{"type": "link", "attrs": {"href": "https://x.com",
                                                                                        "onclick": "x"}}]},
            ]}]}]},
        {"type": "table", "content": [{"type": "tableRow", "content": [
            {"type": "tableCell", "content": [{"type": "paragraph"}]}]}]},
        {"type": "codeBlock", "content": [{"type": "text", "text": "print(1)"}]},
    ]}
    limpo = validar(documento)
    assert mencoes(limpo) == {"7d1c3c55-1111-4111-8111-111111111111"}
    assert "@Ana" in texto_simples(limpo)
    # Atributos estranhos do link são descartados.
    link = limpo["content"][1]["content"][0]["content"][0]["content"][2]["marks"][0]
    assert link == {"type": "link", "attrs": {"href": "https://x.com"}}


@pytest.mark.parametrize("documento,mensagem", [
    ({"type": "doc", "content": [{"type": "script", "text": "x"}]}, "O texto tem um formato que não é aceito."),
    ({"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x", "marks": [
        {"type": "link", "attrs": {"href": "javascript:alert(1)"}}]}]}]},
     "Links precisam começar com http://, https:// ou mailto:."),
    ({"type": "doc", "content": [{"type": "image", "attrs": {"anexoId": "00000000-0000-0000-0000-000000000001"}}]},
     "A imagem precisa ser um anexo deste item."),
    ("<p>html</p>", "O texto tem um formato que não é aceito."),
])
def test_texto_formatado_recusa_o_que_nao_e_permitido(documento, mensagem):
    with pytest.raises(ErroDeRegra) as erro:
        validar(documento, set())
    assert erro.value.mensagem == mensagem


def test_documento_vazio_vira_nada():
    assert validar({"type": "doc", "content": [{"type": "paragraph"}]}) is None


def test_descricao_formatada_no_item_e_no_historico(cenario):
    c = cenario
    item = criar_item(c["adm"], c, descricao=doc("Primeira versão"))
    c["adm"].patch(f"/api/itens/{item['chave']}", json={"dados": {"descricao": doc("Segunda versão")}})
    historico = c["adm"].get(f"/api/itens/{item['chave']}/atividade", params={"filtro": "historico"}).json()
    assert (historico[0]["campo"], historico[0]["valor_anterior"], historico[0]["valor_novo"]) == (
        "Descrição", "Primeira versão", "Segunda versão")


# --- Comentários ------------------------------------------------------------------------------

def test_comentarios_editados_e_excluidos(cenario, db):
    c = cenario
    item = criar_item(c["adm"], c)
    url = f"/api/itens/{item['chave']}"
    # Leitor também comenta (matriz).
    meu = c["leitor"].post(f"{url}/comentarios", json={"corpo": doc("Primeira ideia")}).json()
    do_membro = c["membro"].post(f"{url}/comentarios", json={"corpo": doc("Outra")}).json()

    assert c["leitor"].patch(f"{url}/comentarios/{do_membro['id']}", json={"corpo": doc("x")}).status_code == 403
    assert c["leitor"].patch(f"{url}/comentarios/{meu['id']}", json={"corpo": doc("Ideia revista")}).status_code == 204
    # ADM do espaço pode excluir o de qualquer pessoa.
    assert c["adm"].delete(f"{url}/comentarios/{do_membro['id']}").status_code == 204
    vazio = c["leitor"].post(f"{url}/comentarios", json={"corpo": {"type": "doc", "content": []}})
    assert vazio.json()["detail"] == "Escreva algo antes de enviar."

    comentarios = c["adm"].get(f"{url}/atividade", params={"filtro": "comentarios"}).json()
    excluido, editado = comentarios
    assert excluido["excluido_em"] and excluido["corpo"] is None
    assert excluido["excluido_por"]["nome"] == "Ana Adm"
    assert editado["editado_em"] is not None
    assert texto_simples(editado["corpo"]) == "Ideia revista"
    assert len(eventos(db, "comentario_excluido")) == 1


def test_atividade_junta_comentarios_e_historico_do_mais_recente_para_o_mais_antigo(cenario, relogio_falso):
    c = cenario
    item = criar_item(c["adm"], c)
    url = f"/api/itens/{item['chave']}"
    relogio_falso.avancar(minutes=1)
    c["adm"].post(f"{url}/comentarios", json={"corpo": doc("Comentário")})
    relogio_falso.avancar(minutes=1)
    c["adm"].patch(url, json={"dados": {"resumo": "Novo resumo"}})
    tudo = c["adm"].get(f"{url}/atividade").json()
    assert [(e["tipo"], e.get("campo")) for e in tudo] == [
        ("historico", "Resumo"), ("comentario", None), ("historico", "criado")]


# --- Anexos -----------------------------------------------------------------------------------

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 100


@pytest.fixture(autouse=True)
def pasta_de_anexos(tmp_path, monkeypatch):
    from gerenciador.config import obter_config

    monkeypatch.setattr(obter_config(), "pasta_anexos", str(tmp_path / "anexos"))


def _enviar(cliente, chave, *arquivos):
    return cliente.post(f"/api/itens/{chave}/anexos",
                        files=[("arquivos", (nome, io.BytesIO(conteudo))) for nome, conteudo in arquivos])


def test_anexos_varios_de_uma_vez_e_pre_visualizacao(cenario):
    c = cenario
    item = criar_item(c["adm"], c)
    r = _enviar(c["leitor"], item["chave"], ("print.png", PNG), ("pagina.html", b"<script>alert(1)</script>"),
                ("falso.png", b"<svg onload=alert(1)>"))
    assert r.status_code == 201, r.text
    por_nome = {a["nome_arquivo"]: a for a in r.json()}
    assert por_nome["print.png"]["pre_visualizacao"] is True
    assert por_nome["pagina.html"]["pre_visualizacao"] is False
    # Extensão de imagem com conteúdo que não é imagem: sempre baixado.
    assert por_nome["falso.png"]["pre_visualizacao"] is False

    imagem = c["adm"].get(por_nome["print.png"]["link"])
    assert imagem.status_code == 200 and imagem.content == PNG
    assert imagem.headers["content-type"] == "image/png"
    assert imagem.headers["content-disposition"].startswith("inline")
    html = c["adm"].get(por_nome["pagina.html"]["link"])
    assert html.headers["content-disposition"].startswith("attachment")
    assert html.headers["content-type"] == "application/octet-stream"
    assert "sandbox" in html.headers["content-security-policy"]


def test_link_de_anexo_expira_e_exige_acesso(cenario, novo_cliente):
    c = cenario
    item = criar_item(c["adm"], c)
    anexo = _enviar(c["adm"], item["chave"], ("a.pdf", b"%PDF-1.4 x")).json()[0]
    fora = novo_cliente()
    entrar(fora, "fora@jusbrasil.com.br", "Fora")
    assert fora.get(anexo["link"]).status_code == 404
    adulterado = anexo["link"].replace("assinatura=", "assinatura=0")
    assert c["adm"].get(adulterado).status_code == 403
    assert anexos_svc.link_valido(__import__("uuid").UUID(anexo["id"]), 100, "x") is False


def test_limite_de_tamanho_e_ajuste_pelo_adm(cenario):
    c = cenario
    item = criar_item(c["adm"], c)
    assert c["adm"].put("/api/admin/limite-anexos", json={"limite_mb": 3000}).json()["detail"] == (
        "O limite precisa ficar entre 1 MB e 2048 MB (2 GB).")
    assert c["membro"].put("/api/admin/limite-anexos", json={"limite_mb": 1}).status_code == 403
    assert c["adm"].put("/api/admin/limite-anexos", json={"limite_mb": 1}).status_code == 204
    grande = _enviar(c["adm"], item["chave"], ("grande.zip", b"0" * (1024 * 1024 + 1)))
    assert grande.json()["detail"] == "grande.zip passa do limite de 1 MB por arquivo."
    assert c["adm"].get(f"/api/itens/{item['chave']}").json()["anexos"] == []


def test_excluir_anexo_proprio_ou_como_adm(cenario, db):
    c = cenario
    item = criar_item(c["adm"], c)
    do_leitor = _enviar(c["leitor"], item["chave"], ("l.txt", b"l")).json()[0]
    do_membro = _enviar(c["membro"], item["chave"], ("m.txt", b"m")).json()[0]
    url = f"/api/itens/{item['chave']}/anexos"
    assert do_leitor["pode_excluir"] is True
    assert c["leitor"].delete(f"{url}/{do_membro['id']}").status_code == 403
    assert c["leitor"].delete(f"{url}/{do_leitor['id']}").status_code == 204
    assert c["adm"].delete(f"{url}/{do_membro['id']}").status_code == 204
    assert c["adm"].get(f"/api/itens/{item['chave']}").json()["anexos"] == []
    assert len(eventos(db, "anexo_excluido")) == 2


def test_imagem_na_descricao_precisa_ser_anexo_do_item(cenario):
    c = cenario
    item = criar_item(c["adm"], c)
    anexo = _enviar(c["adm"], item["chave"], ("print.png", PNG)).json()[0]
    com_imagem = {"type": "doc", "content": [{"type": "image", "attrs": {"anexoId": anexo["id"]}}]}
    r = c["adm"].patch(f"/api/itens/{item['chave']}", json={"dados": {"descricao": com_imagem}})
    assert r.status_code == 200
    outro = criar_item(c["adm"], c)
    r2 = c["adm"].patch(f"/api/itens/{outro['chave']}", json={"dados": {"descricao": com_imagem}})
    assert r2.json()["detail"] == "A imagem precisa ser um anexo deste item."


# --- Itens relacionados -----------------------------------------------------------------------

def _vincular(cliente, chave, tipo, outro, **extra):
    return cliente.post(f"/api/itens/{chave}/vinculos", json={"tipo": tipo, "chave": outro, **extra})


def test_vinculo_bidirecional_entre_espacos(cenario, cliente_adm):
    c = cenario
    a = criar_item(c["adm"], c)
    criar_projeto(cliente_adm, sigla="SUP", nome="Suporte")
    b = criar_item(cliente_adm, c, sigla="SUP", responsavel_id=c["adm_id"])
    r = _vincular(c["adm"], b["chave"], "bloqueia", a["chave"])
    assert r.status_code == 201, r.text
    assert [(v["rotulo"], v["chave"]) for v in r.json()] == [("bloqueia", "LOP-1")]
    lado_a = c["adm"].get(f"/api/itens/{a['chave']}").json()["vinculos"]
    assert [(v["rotulo"], v["chave"], v["bloqueio_aberto"]) for v in lado_a] == [("é bloqueado por", "SUP-1", True)]


def test_item_de_espaco_sem_acesso_aparece_restrito(cenario, cliente_adm):
    c = cenario
    a = criar_item(c["adm"], c)
    criar_projeto(cliente_adm, sigla="FIN", nome="Financeiro")
    b = criar_item(cliente_adm, c, sigla="FIN", responsavel_id=c["adm_id"], resumo="Segredo")
    _vincular(cliente_adm, b["chave"], "relacionado", a["chave"])
    visto_pelo_membro = c["membro"].get(f"/api/itens/{a['chave']}").json()["vinculos"]
    assert visto_pelo_membro == [{
        "id": visto_pelo_membro[0]["id"], "tipo": "relacionado", "rotulo": "relacionado a", "chave": "FIN-1",
        "acesso_restrito": True, "resumo": None, "status": None, "status_categoria": None, "bloqueio_aberto": False}]
    # E ele não consegue criar vínculo com item que não vê.
    assert _vincular(c["membro"], a["chave"], "relacionado", "FIN-1").status_code == 404


def test_validacoes_de_vinculo(cenario):
    c = cenario
    a, b = criar_item(c["adm"], c), criar_item(c["adm"], c)
    assert _vincular(c["adm"], a["chave"], "bloqueia", a["chave"]).json()["detail"] == (
        "Um item não pode ser vinculado a ele mesmo.")
    _vincular(c["adm"], a["chave"], "relacionado", b["chave"])
    # "Relacionado a" é o mesmo vínculo nos dois sentidos.
    assert _vincular(c["adm"], b["chave"], "relacionado", a["chave"]).json()["detail"] == "Esse vínculo já existe."
    assert _vincular(c["adm"], a["chave"], "inventado", b["chave"]).json()["detail"] == "Tipo de vínculo inválido."
    assert _vincular(c["leitor"], a["chave"], "causa", b["chave"]).status_code == 403


def test_bloqueio_circular_avisa_e_permite_confirmar(cenario):
    c = cenario
    a, b, d = criar_item(c["adm"], c), criar_item(c["adm"], c), criar_item(c["adm"], c)
    _vincular(c["adm"], a["chave"], "bloqueia", b["chave"])
    _vincular(c["adm"], b["chave"], "bloqueia", d["chave"])
    aviso = _vincular(c["adm"], d["chave"], "bloqueia", a["chave"])
    assert aviso.status_code == 409
    assert aviso.json()["detail"]["codigo"] == "bloqueio_circular"
    assert _vincular(c["adm"], d["chave"], "bloqueia", a["chave"], confirmar_ciclo=True).status_code == 201


def test_vinculo_entra_no_historico_dos_dois_itens_e_pode_ser_removido(cenario):
    c = cenario
    a, b = criar_item(c["adm"], c), criar_item(c["adm"], c)
    vinculo = _vincular(c["membro"], a["chave"], "duplica", b["chave"]).json()[0]
    hist_b = c["adm"].get(f"/api/itens/{b['chave']}/atividade", params={"filtro": "historico"}).json()
    assert (hist_b[0]["campo"], hist_b[0]["valor_novo"]) == ("Itens relacionados", "é duplicado por LOP-1")
    assert c["membro"].delete(f"/api/itens/{b['chave']}/vinculos/{vinculo['id']}").status_code == 204
    assert c["adm"].get(f"/api/itens/{a['chave']}").json()["vinculos"] == []


def test_concluir_item_bloqueado_pede_confirmacao_e_registra(cenario, db):
    c = cenario
    a, b = criar_item(c["adm"], c), criar_item(c["adm"], c)
    _vincular(c["adm"], a["chave"], "bloqueia", b["chave"])
    concluir = {"dados": {"status_id": c["status"]["Concluído"]}}
    aviso = c["adm"].patch(f"/api/itens/{b['chave']}", json=concluir)
    assert aviso.status_code == 409
    assert aviso.json()["detail"] == {"mensagem": "Este item ainda é bloqueado por: LOP-1. Concluir mesmo assim?",
                                      "codigo": "concluir_bloqueado", "bloqueios": ["LOP-1"]}
    assert c["adm"].get(f"/api/itens/{b['chave']}").json()["status"]["nome"] == "A fazer"
    ok = c["adm"].patch(f"/api/itens/{b['chave']}", json={**concluir, "confirmar_bloqueio": True})
    assert ok.json()["status"]["nome"] == "Concluído"
    historico = c["adm"].get(f"/api/itens/{b['chave']}/atividade", params={"filtro": "historico"}).json()
    assert "Conclusão com bloqueio aberto" in [h["campo"] for h in historico]
    assert eventos(db, "conclusao_com_bloqueio")[0].detalhes["bloqueios"] == ["LOP-1"]
    # Quando o bloqueio termina, concluir não pede confirmação.
    c["adm"].patch(f"/api/itens/{a['chave']}", json=concluir)
    assert c["adm"].get(f"/api/itens/{b['chave']}").json()["vinculos"][0]["bloqueio_aberto"] is False


def test_busca_de_itens_para_vincular(cenario):
    c = cenario
    criar_item(c["adm"], c, resumo="Padronizar petição")
    assert [i["chave"] for i in c["membro"].get("/api/itens/busca", params={"q": "petição"}).json()] == ["LOP-1"]
    assert [i["chave"] for i in c["membro"].get("/api/itens/busca", params={"q": "lop-1"}).json()] == ["LOP-1"]
