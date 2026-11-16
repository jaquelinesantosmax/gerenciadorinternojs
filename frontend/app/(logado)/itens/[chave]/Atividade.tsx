"use client";

import { useCallback, useEffect, useState } from "react";
import { Avatar } from "@/components/Avatar";
import { Dialogo } from "@/components/Dialogo";
import { Editor, paraEditar } from "@/components/Editor";
import { TextoRico } from "@/components/TextoRico";
import { api, ErroApi, type DocTexto, type EventoAtividade, type Pessoa } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";

type Filtro = "tudo" | "comentarios" | "historico";

const vazio = (doc: DocTexto | null) => !doc || !JSON.stringify(doc).match(/"text":"\s*\S|"type":"(image|mention)"/);

/** Comentários e histórico na linha do tempo da prévia v3, do mais recente para o mais antigo. */
export function Atividade({
  chave,
  podeComentar,
  pessoas,
  imagens,
  aoEnviarImagem,
  versao,
}: {
  chave: string;
  podeComentar: boolean;
  pessoas: Pessoa[];
  imagens: Record<string, string>;
  aoEnviarImagem: (arquivo: File) => Promise<{ id: string; link: string } | null>;
  /** Muda quando o item é alterado, para recarregar o histórico. */
  versao: string;
}) {
  const [filtro, setFiltro] = useState<Filtro>("tudo");
  const [eventos, setEventos] = useState<EventoAtividade[] | null>(null);
  const [novo, setNovo] = useState<DocTexto | null>(null);
  const [chaveEditor, setChaveEditor] = useState(0);
  const [editando, setEditando] = useState<{ id: string; corpo: DocTexto | null } | null>(null);
  const [excluir, setExcluir] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(async () => {
    setEventos(await api.atividade(chave, filtro).catch(() => []));
  }, [chave, filtro]);

  useEffect(() => {
    void carregar();
  }, [carregar, versao]);

  async function enviar() {
    if (vazio(novo)) {
      setErro("Escreva algo antes de enviar.");
      return;
    }
    setOcupado(true);
    setErro(null);
    try {
      await api.comentar(chave, novo as DocTexto);
      setNovo(null);
      setChaveEditor((n) => n + 1);
      await carregar();
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível comentar.");
    } finally {
      setOcupado(false);
    }
  }

  async function salvarEdicao() {
    if (!editando) return;
    setOcupado(true);
    try {
      await api.editarComentario(chave, editando.id, editando.corpo as DocTexto);
      setEditando(null);
      await carregar();
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível salvar.");
    } finally {
      setOcupado(false);
    }
  }

  async function confirmarExclusao() {
    if (!excluir) return;
    setOcupado(true);
    try {
      await api.excluirComentario(chave, excluir);
      setExcluir(null);
      await carregar();
    } finally {
      setOcupado(false);
    }
  }

  const abas: [Filtro, string][] = [
    ["tudo", "Atividade"],
    ["comentarios", "Comentários"],
    ["historico", "Histórico"],
  ];

  return (
    <section aria-labelledby="titulo-atividade" style={{ marginTop: 26 }}>
      <h2 id="titulo-atividade" className="oculto-acessivel">
        Comentários e histórico
      </h2>
      {podeComentar && (
        <div>
          <Editor key={chaveEditor} rotulo="Novo comentário" valor={null} aoMudar={setNovo} pessoas={pessoas} aoEnviarImagem={aoEnviarImagem} />
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 6 }}>
            <span className="legenda">Use @ para mencionar alguém. Chaves de item (ex.: LOP-12) viram link.</span>
            <button className="botao botao-acao" onClick={() => void enviar()} disabled={ocupado}>
              Comentar
            </button>
          </div>
        </div>
      )}
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <div role="tablist" aria-label="Filtrar atividade" style={{ display: "flex", gap: 4, marginTop: 18 }}>
        {abas.map(([valor, nome]) => (
          <button key={valor} role="tab" aria-selected={filtro === valor} className={`aba${filtro === valor ? " ativa" : ""}`} onClick={() => setFiltro(valor)}>
            {nome}
          </button>
        ))}
      </div>
      {eventos === null ? (
        <p className="legenda">Carregando…</p>
      ) : eventos.length === 0 ? (
        <p className="legenda">Nada por aqui ainda.</p>
      ) : (
        <ol className="trilho" style={{ listStyle: "none", margin: "10px 0 0" }}>
          {eventos.map((e) => {
            if (e.tipo === "historico") {
              return (
                <li key={`h${e.id}`} className="evento">
                  <span className="ponto" aria-hidden="true" />
                  <span className="legenda">{formatarDataHora(e.quando)}</span>{" "}
                  <span style={{ fontSize: 13, color: "var(--texto-2)" }}>
                    {e.autor?.nome ?? "Sistema"} {descreverMudanca(e)}
                  </span>
                </li>
              );
            }
            if (e.excluido_em) {
              return (
                <li key={`c${e.id}`} className="evento">
                  <span className="ponto ponto-excluido" aria-hidden="true" />
                  <span className="legenda">
                    Comentário excluído por {e.excluido_por?.nome ?? "—"} em {formatarDataHora(e.excluido_em)}
                  </span>
                </li>
              );
            }
            return (
              <li key={`c${e.id}`} className="evento comentario">
                <span className="ponto ponto-comentario" aria-hidden="true" />
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <Avatar nome={e.autor?.nome ?? "?"} fotoUrl={e.autor?.foto_url} tamanho={22} />
                  <span style={{ fontWeight: 500 }}>{e.autor?.nome}</span>
                  <span className="legenda">
                    {formatarDataHora(e.quando)}
                    {e.editado_em ? ", editado" : ""}
                  </span>
                  {e.pode_editar && editando?.id !== e.id && (
                    <span style={{ marginLeft: "auto", display: "flex", gap: 4 }}>
                      <button className="botao botao-discreto" onClick={() => setEditando({ id: e.id, corpo: e.corpo ?? null })}>
                        Editar
                      </button>
                      <button className="botao botao-discreto" onClick={() => setExcluir(e.id)}>
                        Excluir
                      </button>
                    </span>
                  )}
                </div>
                {editando?.id === e.id ? (
                  <div style={{ marginTop: 6 }}>
                    <Editor rotulo="Editar comentário" valor={paraEditar(e.corpo, imagens)} aoMudar={(d) => setEditando({ id: e.id, corpo: d })} pessoas={pessoas} aoEnviarImagem={aoEnviarImagem} autoFoco />
                    <div style={{ display: "flex", gap: 6, justifyContent: "flex-end", marginTop: 6 }}>
                      <button className="botao" onClick={() => setEditando(null)}>
                        Cancelar
                      </button>
                      <button className="botao botao-acao" onClick={() => void salvarEdicao()} disabled={ocupado}>
                        Salvar
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="balao">
                    <TextoRico doc={e.corpo} imagens={imagens} />
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}
      <Dialogo aberto={excluir !== null} titulo="Excluir comentário?" textoConfirmar="Excluir" perigo ocupado={ocupado} aoConfirmar={() => void confirmarExclusao()} aoCancelar={() => setExcluir(null)}>
        No lugar dele fica a linha &quot;comentário excluído por você&quot;, com a data.
      </Dialogo>
      <style>{`
        .aba{border:none;background:none;font-size:13px;color:var(--texto-2);padding:5px 10px;border-radius:20px;cursor:pointer}
        .aba.ativa{background:var(--verde-fundo);color:var(--verde-escuro);font-weight:500}
        .evento.comentario .ponto-comentario{left:-21px;top:13px;width:11px;height:11px;background:var(--verde)}
        .evento .ponto-excluido{background:#fff;border:1.5px solid #b4b2a9}
        .balao{margin-top:4px;border:0.5px solid var(--borda);border-radius:8px;padding:8px 10px;background:#fff}
      `}</style>
    </section>
  );
}

export function descreverMudanca(e: EventoAtividade): string {
  if (e.campo === "criado") return `criou o item`;
  if (e.campo === "Conclusão com bloqueio aberto") return `concluiu com bloqueio aberto. ${e.valor_novo ?? ""}`;
  if (e.campo === "Anexos") return e.valor_novo ? `anexou ${e.valor_novo}` : `excluiu o anexo ${e.valor_anterior}`;
  if (e.campo === "Itens relacionados") return e.valor_novo ? `vinculou: ${e.valor_novo}` : `desvinculou: ${e.valor_anterior}`;
  if (!e.valor_anterior) return `preencheu ${e.campo}: ${e.valor_novo}`;
  if (!e.valor_novo) return `limpou ${e.campo} (era ${e.valor_anterior})`;
  return `mudou ${e.campo}: ${e.valor_anterior} → ${e.valor_novo}`;
}
