"use client";

import { IconArrowDown, IconArrowUp, IconPlus, IconTrash } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { api, ErroApi, type QuadroResumo, type StatusWorkflow } from "@/lib/api";

const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);
const NOMES_TIPO: Record<string, string> = { kanban: "Kanban", simples: "Simples", scrum: "Scrum" };

interface ColunaEditavel {
  nome: string;
  limite: string;
  status_ids: string[];
}

function EditorColunas({ quadro, ligados, aoSalvar }: { quadro: QuadroResumo; ligados: StatusWorkflow[]; aoSalvar: () => void }) {
  const [colunas, setColunas] = useState<ColunaEditavel[] | null>(null);
  const [usaBacklog, setUsaBacklog] = useState(quadro.usa_backlog);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    const detalhe = await api.quadro(quadro.id);
    setUsaBacklog(detalhe.usa_backlog);
    setColunas(detalhe.colunas.map((c) => ({ nome: c.nome, limite: c.limite ? String(c.limite) : "", status_ids: c.status.map((s) => s.id) })));
  }, [quadro.id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (!colunas) return <p className="legenda">Carregando…</p>;
  const usados = new Set(colunas.flatMap((c) => c.status_ids));
  const semColuna = ligados.filter((s) => !usados.has(s.id) && !(usaBacklog && s.nome === "Backlog"));
  const mudar = (i: number, nova: Partial<ColunaEditavel>) => setColunas(colunas.map((c, j) => (j === i ? { ...c, ...nova } : c)));
  const mover = (i: number, d: number) => {
    const copia = [...colunas];
    [copia[i], copia[i + d]] = [copia[i + d], copia[i]];
    setColunas(copia);
  };

  async function salvar() {
    setErro(null);
    setAviso(null);
    try {
      await api.definirColunas(quadro.id, colunas!.map((c) => ({ nome: c.nome, limite: c.limite ? Number(c.limite) : null, status_ids: c.status_ids })));
      setAviso("Colunas salvas.");
      aoSalvar();
    } catch (f) {
      setErro(msg(f, "Não foi possível salvar."));
    }
  }

  return (
    <div>
      {quadro.tipo !== "simples" && (
        <label style={{ display: "flex", gap: 6, alignItems: "center", marginBottom: 10 }}>
          <input
            type="checkbox"
            checked={usaBacklog}
            onChange={async (e) => {
              try {
                await api.alterarQuadro(quadro.id, { usa_backlog: e.target.checked });
                await carregar();
                aoSalvar();
              } catch (f) {
                setErro(msg(f, "Não foi possível alterar."));
              }
            }}
          />
          Backlog numa área separada, fora das colunas
        </label>
      )}
      <div style={{ display: "grid", gap: 8 }}>
        {colunas.map((c, i) => (
          <div key={i} className="editor-coluna">
            <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input className="campo" aria-label="Nome da coluna" value={c.nome} onChange={(e) => mudar(i, { nome: e.target.value })} style={{ flex: 1 }} />
              <input className="campo" aria-label="Limite de itens" type="number" min={1} placeholder="Sem limite" value={c.limite} onChange={(e) => mudar(i, { limite: e.target.value })} style={{ width: 110 }} />
              <button className="botao botao-discreto" aria-label="Subir coluna" disabled={i === 0} onClick={() => mover(i, -1)}>
                <IconArrowUp size={14} stroke={1.5} />
              </button>
              <button className="botao botao-discreto" aria-label="Descer coluna" disabled={i === colunas.length - 1} onClick={() => mover(i, 1)}>
                <IconArrowDown size={14} stroke={1.5} />
              </button>
              <button className="botao botao-discreto" aria-label={`Tirar a coluna ${c.nome}`} onClick={() => setColunas(colunas.filter((_, j) => j !== i))}>
                <IconTrash size={14} stroke={1.5} />
              </button>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", marginTop: 6 }}>
              {ligados
                .filter((s) => c.status_ids.includes(s.id) || !usados.has(s.id))
                .map((s) => (
                  <label key={s.id} style={{ display: "inline-flex", gap: 5, alignItems: "center", fontSize: 13 }}>
                    <input type="checkbox" checked={c.status_ids.includes(s.id)} onChange={(e) => mudar(i, { status_ids: e.target.checked ? [...c.status_ids, s.id] : c.status_ids.filter((x) => x !== s.id) })} />
                    {s.nome}
                  </label>
                ))}
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 10, flexWrap: "wrap" }}>
        <button className="botao" onClick={() => setColunas([...colunas, { nome: "Nova coluna", limite: "", status_ids: [] }])}>
          <IconPlus size={14} stroke={1.5} /> Coluna
        </button>
        <button className="botao botao-acao" onClick={() => void salvar()}>
          Salvar colunas
        </button>
        {aviso && <span className="legenda">{aviso}</span>}
      </div>
      {semColuna.length > 0 && (
        <p className="legenda">Status sem coluna (os itens neles não aparecem no quadro): {semColuna.map((s) => s.nome).join(", ")}.</p>
      )}
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
    </div>
  );
}

/** Quadros do espaço: colunas (que juntam status), limite de itens e backlog. */
export function ConfigQuadros({ sigla, versao }: { sigla: string; versao: number }) {
  const [quadros, setQuadros] = useState<QuadroResumo[]>([]);
  const [ligados, setLigados] = useState<StatusWorkflow[]>([]);
  const [aberto, setAberto] = useState<string | null>(null);
  const [novo, setNovo] = useState({ nome: "", tipo: "kanban" });
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    setQuadros(await api.quadros(sigla));
    setLigados((await api.workflow(sigla)).ligados);
  }, [sigla]);

  useEffect(() => {
    void carregar();
  }, [carregar, versao]);

  return (
    <div>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {quadros.map((q) => (
          <li key={q.id} style={{ borderBottom: "0.5px solid var(--borda)", padding: "8px 0" }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <span style={{ flex: 1 }}>
                <b style={{ fontWeight: 500 }}>{q.nome}</b> <span className="legenda">· {NOMES_TIPO[q.tipo]}{q.painel_id ? " · quadro do painel" : ""}</span>
              </span>
              <button className="botao botao-discreto" onClick={() => setAberto(aberto === q.id ? null : q.id)}>
                {aberto === q.id ? "Fechar" : "Editar colunas"}
              </button>
              {!q.painel_id && (
                <button
                  className="botao botao-discreto"
                  aria-label={`Excluir o quadro ${q.nome}`}
                  onClick={async () => {
                    if (!window.confirm(`Excluir o quadro ${q.nome}? Os itens não são afetados.`)) return;
                    try {
                      await api.excluirQuadro(q.id);
                      await carregar();
                    } catch (f) {
                      setErro(msg(f, "Não foi possível excluir."));
                    }
                  }}
                >
                  <IconTrash size={14} stroke={1.5} />
                </button>
              )}
            </div>
            {aberto === q.id && (
              <div style={{ marginTop: 10 }}>
                <EditorColunas quadro={q} ligados={ligados} aoSalvar={() => void carregar()} />
              </div>
            )}
          </li>
        ))}
      </ul>
      <form
        style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap", alignItems: "flex-end" }}
        onSubmit={async (e) => {
          e.preventDefault();
          setErro(null);
          try {
            await api.criarQuadro(sigla, novo.nome, novo.tipo);
            setNovo({ nome: "", tipo: novo.tipo });
            await carregar();
          } catch (f) {
            setErro(msg(f, "Não foi possível criar."));
          }
        }}
      >
        <div style={{ flex: 1, minWidth: 200 }}>
          <label className="rotulo" htmlFor="novo-quadro">
            Novo quadro sobre os mesmos itens
          </label>
          <input id="novo-quadro" className="campo" placeholder="Ex.: Acompanhamento semanal" value={novo.nome} onChange={(e) => setNovo({ ...novo, nome: e.target.value })} />
        </div>
        <div>
          <label className="rotulo" htmlFor="tipo-quadro">
            Tipo
          </label>
          <select id="tipo-quadro" className="campo" value={novo.tipo} onChange={(e) => setNovo({ ...novo, tipo: e.target.value })}>
            <option value="kanban">Kanban</option>
            <option value="simples">Simples</option>
          </select>
        </div>
        <button className="botao botao-acao" type="submit" disabled={!novo.nome.trim()} style={{ height: 36 }}>
          Criar quadro
        </button>
      </form>
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <style>{`.editor-coluna{border:0.5px solid var(--borda);border-radius:8px;padding:8px 10px;background:#fff}`}</style>
    </div>
  );
}
