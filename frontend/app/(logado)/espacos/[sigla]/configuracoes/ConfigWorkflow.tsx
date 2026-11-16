"use client";

import { IconPlus, IconTrash } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { Dialogo } from "@/components/Dialogo";
import { EtiquetaStatus } from "@/components/EtiquetaStatus";
import { api, ErroApi, type Workflow } from "@/lib/api";

export const NOMES_CATEGORIA: Record<string, string> = { a_fazer: "A fazer", em_andamento: "Em andamento", concluido: "Concluído" };
const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);

/** Status ligados no espaço, status próprios e o fluxo de transições (matriz "de → para"). */
export function ConfigWorkflow({ sigla, aoMudar }: { sigla: string; aoMudar: () => void }) {
  const [wf, setWf] = useState<Workflow | null>(null);
  const [pares, setPares] = useState<Set<string>>(new Set());
  const [alterado, setAlterado] = useState(false);
  const [novo, setNovo] = useState({ nome: "", categoria: "em_andamento" });
  const [parecido, setParecido] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const aplicar = useCallback((w: Workflow) => {
    setWf(w);
    setPares(new Set(w.transicoes.map(([de, para]) => `${de}|${para}`)));
    setAlterado(false);
  }, []);

  useEffect(() => {
    api.workflow(sigla).then(aplicar).catch((f) => setErro(msg(f, "Não foi possível carregar.")));
  }, [sigla, aplicar]);

  const executar = async (acao: () => Promise<Workflow>) => {
    setErro(null);
    setAviso(null);
    try {
      aplicar(await acao());
      aoMudar();
    } catch (f) {
      setErro(msg(f, "Não foi possível concluir."));
    }
  };

  async function criar(confirmar = false) {
    setErro(null);
    try {
      aplicar(await api.criarStatus(sigla, novo.nome, novo.categoria, confirmar));
      setNovo({ nome: "", categoria: novo.categoria });
      setParecido(null);
      aoMudar();
    } catch (f) {
      if (f instanceof ErroApi && f.codigo === "status_parecido") setParecido(f.message);
      else setErro(msg(f, "Não foi possível criar."));
    }
  }

  if (!wf) return <p className="legenda">{erro ?? "Carregando…"}</p>;

  const alternar = (de: string, para: string) => {
    const chave = `${de}|${para}`;
    const novo = new Set(pares);
    if (novo.has(chave)) novo.delete(chave);
    else novo.add(chave);
    setPares(novo);
    setAlterado(true);
  };

  return (
    <div>
      <h3 className="h3" style={{ marginBottom: 6 }}>
        Status ligados neste espaço
      </h3>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {wf.ligados.map((s) => (
          <li key={s.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: "0.5px solid var(--borda)" }}>
            <EtiquetaStatus nome={s.nome} categoria={s.categoria} />
            <span className="legenda" style={{ flex: 1 }}>
              {NOMES_CATEGORIA[s.categoria]} · {s.proprio ? "próprio deste espaço" : "padrão"} · {s.itens} item(ns)
            </span>
            <button
              className="botao botao-discreto"
              aria-label={`${s.proprio ? "Apagar" : "Desligar"} ${s.nome}`}
              title={s.itens ? "Mova os itens antes" : s.proprio ? "Apagar" : "Desligar"}
              disabled={s.itens > 0}
              onClick={() => void executar(() => api.desligarStatus(sigla, s.id))}
            >
              <IconTrash size={14} stroke={1.5} /> {s.proprio ? "Apagar" : "Desligar"}
            </button>
          </li>
        ))}
      </ul>
      {wf.disponiveis.length > 0 && (
        <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
          <span className="legenda">Padrões desligados:</span>
          {wf.disponiveis.map((s) => (
            <button key={s.id} className="botao" onClick={() => void executar(() => api.ligarStatus(sigla, s.id))}>
              <IconPlus size={13} stroke={1.5} /> {s.nome}
            </button>
          ))}
        </div>
      )}
      <form
        style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap", alignItems: "flex-end" }}
        onSubmit={(e) => {
          e.preventDefault();
          if (novo.nome.trim()) void criar();
        }}
      >
        <div style={{ flex: 1, minWidth: 200 }}>
          <label className="rotulo" htmlFor="novo-status">
            Novo status próprio
          </label>
          <input id="novo-status" className="campo" placeholder="Ex.: Em revisão jurídica" value={novo.nome} onChange={(e) => setNovo({ ...novo, nome: e.target.value })} />
        </div>
        <div>
          <label className="rotulo" htmlFor="categoria-status">
            Categoria
          </label>
          <select id="categoria-status" className="campo" value={novo.categoria} onChange={(e) => setNovo({ ...novo, categoria: e.target.value })}>
            {Object.entries(NOMES_CATEGORIA).map(([v, n]) => (
              <option key={v} value={v}>
                {n}
              </option>
            ))}
          </select>
        </div>
        <button className="botao botao-acao" type="submit" disabled={!novo.nome.trim()} style={{ height: 36 }}>
          Criar status
        </button>
      </form>
      <p className="legenda" style={{ margin: "6px 0 0" }}>
        O status próprio só existe neste espaço. A categoria diz como ele conta nos painéis e relatórios. Ele ganha uma coluna no fim de cada quadro.
      </p>

      <h3 className="h3" style={{ margin: "20px 0 4px" }}>
        Fluxo de transições
      </h3>
      <p className="legenda" style={{ margin: "0 0 8px" }}>
        Marque para onde um item pode ir a partir de cada status. Linha: status atual. Coluna: para onde vai.
      </p>
      <div style={{ overflowX: "auto" }}>
        <table className="matriz">
          <thead>
            <tr>
              <th scope="col">De ↓ / Para →</th>
              {wf.ligados.map((s) => (
                <th key={s.id} scope="col">
                  <span>{s.nome}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {wf.ligados.map((de) => (
              <tr key={de.id}>
                <th scope="row">{de.nome}</th>
                {wf.ligados.map((para) => (
                  <td key={para.id}>
                    {de.id === para.id ? (
                      <span className="legenda">—</span>
                    ) : (
                      <input type="checkbox" aria-label={`De ${de.nome} para ${para.nome}`} checked={pares.has(`${de.id}|${para.id}`)} onChange={() => alternar(de.id, para.id)} />
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 10 }}>
        <button
          className="botao botao-acao"
          disabled={!alterado}
          onClick={async () => {
            await executar(() => api.definirTransicoes(sigla, [...pares].map((p) => p.split("|") as [string, string])));
            setAviso("Fluxo salvo.");
          }}
        >
          Salvar fluxo
        </button>
        {alterado && (
          <button className="botao" onClick={() => aplicar(wf)}>
            Desfazer mudanças
          </button>
        )}
        {aviso && <span className="legenda">{aviso}</span>}
      </div>
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <Dialogo aberto={parecido !== null} titulo="Nome parecido" textoConfirmar="Criar mesmo assim" aoConfirmar={() => void criar(true)} aoCancelar={() => setParecido(null)}>
        {parecido} Status repetidos com nomes diferentes (como &quot;BLOCKED&quot; e &quot;Bloqueado&quot;) confundem os relatórios.
      </Dialogo>
      <style>{`
        .matriz{border-collapse:collapse;font-size:12px}
        .matriz th,.matriz td{border:0.5px solid var(--borda);padding:5px 8px;text-align:center}
        .matriz thead th{font-weight:500;color:var(--texto-2);vertical-align:bottom;max-width:90px}
        .matriz tbody th{text-align:left;font-weight:500;white-space:nowrap;background:var(--fundo)}
        .matriz input{cursor:pointer}
      `}</style>
    </div>
  );
}
