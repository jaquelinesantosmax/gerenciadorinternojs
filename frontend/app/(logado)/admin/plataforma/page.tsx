"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useEu } from "@/components/Moldura";
import { SemPermissao } from "@/components/SemPermissao";
import { api, ErroApi, type StatusCatalogo } from "@/lib/api";

const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);

/** Ajustes da plataforma: status padrão e limite de anexos (ADM da plataforma). */
export default function PaginaPlataforma() {
  const { eu } = useEu();
  const [limite, setLimite] = useState("");
  const [avisoLimite, setAvisoLimite] = useState<string | null>(null);
  const pode = eu.permissoes.definir_limite_anexos;

  const carregar = useCallback(async () => {
    setLimite(String((await api.limiteAnexos()).limite_mb));
  }, []);

  useEffect(() => {
    if (pode) void carregar();
  }, [carregar, pode]);

  if (!pode) return <SemPermissao />;

  return (
    <div style={{ maxWidth: 720 }}>
      <h1 className="h1">Plataforma</h1>
      <p className="legenda" style={{ marginTop: 8 }}>
        Os times agora têm cadastro próprio, com membros, na página <Link href="/times">Times</Link> do menu.
      </p>

      <CatalogoStatus />

      <section className="painel" style={{ marginTop: 16 }}>
        <h2 className="h2">Limite de anexos</h2>
        <p className="legenda" style={{ margin: "4px 0 10px" }}>
          Tamanho máximo de cada arquivo. Padrão do Jira Cloud: 1 GB (1024 MB), ajustável até 2 GB (2048 MB).
        </p>
        <form
          style={{ display: "flex", gap: 8, alignItems: "center" }}
          onSubmit={async (e) => {
            e.preventDefault();
            setAvisoLimite(null);
            try {
              await api.definirLimiteAnexos(Number(limite));
              setAvisoLimite("Salvo.");
            } catch (f) {
              setAvisoLimite(msg(f, "Não foi possível salvar."));
            }
          }}
        >
          <input className="campo" style={{ width: 140 }} type="number" min={1} max={2048} aria-label="Limite em MB" value={limite} onChange={(e) => setLimite(e.target.value)} />
          <span>MB por arquivo</span>
          <button className="botao botao-acao" type="submit">
            Salvar
          </button>
          {avisoLimite && <span className="legenda">{avisoLimite}</span>}
        </form>
      </section>
    </div>
  );
}

const NOMES_CATEGORIA: Record<string, string> = { a_fazer: "A fazer", em_andamento: "Em andamento", concluido: "Concluído" };

/** Catálogo de status padrão (ADM da plataforma) e promoção de status de espaço a padrão. */
function CatalogoStatus() {
  const [lista, setLista] = useState<StatusCatalogo[]>([]);
  const [novo, setNovo] = useState({ nome: "", categoria: "em_andamento" });
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    api.catalogoStatus().then(setLista).catch(() => setLista([]));
  }, []);

  async function criar(confirmar = false) {
    setErro(null);
    try {
      setLista(await api.criarStatusPadrao(novo.nome, novo.categoria, confirmar));
      setNovo({ ...novo, nome: "" });
    } catch (f) {
      if (f instanceof ErroApi && f.codigo === "status_parecido" && window.confirm(f.message)) await criar(true);
      else setErro(msg(f, "Não foi possível criar."));
    }
  }

  const padrao = lista.filter((s) => !s.espaco);
  const proprios = lista.filter((s) => s.espaco);
  return (
    <section className="painel" style={{ marginTop: 16 }}>
      <h2 className="h2">Status padrão</h2>
      <p className="legenda" style={{ margin: "4px 0 10px" }}>
        Ficam disponíveis como opção em todos os espaços; cada ADM de espaço liga os que quiser. Status novo não é imposto a ninguém.
      </p>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {padrao.map((s) => (
          <span key={s.id} className={`etiqueta status-${s.categoria}`} title={NOMES_CATEGORIA[s.categoria]}>
            {s.nome}
          </span>
        ))}
      </div>
      <form
        style={{ display: "flex", gap: 8, marginTop: 12, flexWrap: "wrap" }}
        onSubmit={(e) => {
          e.preventDefault();
          if (novo.nome.trim()) void criar();
        }}
      >
        <input className="campo" style={{ flex: 1, minWidth: 180 }} aria-label="Nome do novo status padrão" placeholder="Novo status padrão" value={novo.nome} onChange={(e) => setNovo({ ...novo, nome: e.target.value })} />
        <select className="campo" style={{ width: 160 }} aria-label="Categoria" value={novo.categoria} onChange={(e) => setNovo({ ...novo, categoria: e.target.value })}>
          {Object.entries(NOMES_CATEGORIA).map(([v, n]) => (
            <option key={v} value={v}>
              {n}
            </option>
          ))}
        </select>
        <button className="botao botao-acao" type="submit" disabled={!novo.nome.trim()}>
          Criar
        </button>
      </form>
      {proprios.length > 0 && (
        <>
          <h3 className="h3" style={{ margin: "16px 0 6px" }}>
            Status próprios dos espaços
          </h3>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {proprios.map((s) => (
              <li key={s.id} style={{ display: "flex", gap: 8, alignItems: "center", padding: "5px 0", borderBottom: "0.5px solid var(--borda)" }}>
                <span style={{ flex: 1 }}>
                  {s.nome} <span className="legenda">· {s.espaco} · {NOMES_CATEGORIA[s.categoria]}</span>
                </span>
                <button
                  className="botao botao-discreto"
                  onClick={async () => {
                    try {
                      setLista(await api.promoverStatus(s.id));
                    } catch (f) {
                      setErro(msg(f, "Não foi possível promover."));
                    }
                  }}
                >
                  Tornar padrão
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
    </section>
  );
}
