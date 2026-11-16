"use client";

import { useCallback, useEffect, useState } from "react";
import { useEu } from "@/components/Moldura";
import { SemPermissao } from "@/components/SemPermissao";
import { api, ErroApi, type TimeItem } from "@/lib/api";

const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);

/** Ajustes da plataforma: lista provisória de Times e limite de anexos (ADM da plataforma). */
export default function PaginaPlataforma() {
  const { eu } = useEu();
  const [times, setTimes] = useState<TimeItem[]>([]);
  const [novo, setNovo] = useState("");
  const [limite, setLimite] = useState("");
  const [erroTimes, setErroTimes] = useState<string | null>(null);
  const [avisoLimite, setAvisoLimite] = useState<string | null>(null);
  const pode = eu.permissoes.gerenciar_times_provisorios;

  const carregar = useCallback(async () => {
    setTimes(await api.times(true));
    setLimite(String((await api.limiteAnexos()).limite_mb));
  }, []);

  useEffect(() => {
    if (pode) void carregar();
  }, [carregar, pode]);

  if (!pode) return <SemPermissao />;

  return (
    <div style={{ maxWidth: 720 }}>
      <h1 className="h1">Plataforma</h1>
      <section className="painel" style={{ marginTop: 16 }}>
        <h2 className="h2">Times</h2>
        <p className="legenda" style={{ margin: "4px 0 10px" }}>
          Lista provisória para o campo Time dos itens, até o cadastro de Times com membros chegar na Etapa 4. Time desativado sai da
          lista de escolha, mas continua nos itens que já o usam.
        </p>
        <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
          {times.map((t) => (
            <li key={t.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: "0.5px solid var(--borda)", opacity: t.ativo ? 1 : 0.55 }}>
              <span style={{ flex: 1 }}>
                {t.nome} {!t.ativo && <span className="etiqueta etiqueta-neutra">Desativado</span>}
              </span>
              <button
                className="botao botao-discreto"
                onClick={async () => {
                  const nome = window.prompt("Novo nome do time", t.nome);
                  if (!nome || nome === t.nome) return;
                  try {
                    await api.alterarTime(t.id, { nome });
                    await carregar();
                  } catch (f) {
                    setErroTimes(msg(f, "Não foi possível renomear."));
                  }
                }}
              >
                Renomear
              </button>
              <button
                className="botao botao-discreto"
                onClick={async () => {
                  await api.alterarTime(t.id, { ativo: !t.ativo });
                  await carregar();
                }}
              >
                {t.ativo ? "Desativar" : "Reativar"}
              </button>
            </li>
          ))}
          {times.length === 0 && <li className="legenda">Nenhum time ainda. Sem times, ninguém consegue criar itens.</li>}
        </ul>
        <form
          style={{ display: "flex", gap: 8, marginTop: 10 }}
          onSubmit={async (e) => {
            e.preventDefault();
            setErroTimes(null);
            try {
              await api.criarTime(novo);
              setNovo("");
              await carregar();
            } catch (f) {
              setErroTimes(msg(f, "Não foi possível criar."));
            }
          }}
        >
          <input className="campo" aria-label="Nome do novo time" placeholder="Nome do time (ex.: Legal Ops)" value={novo} onChange={(e) => setNovo(e.target.value)} />
          <button className="botao botao-acao" type="submit" disabled={!novo.trim()}>
            Adicionar
          </button>
        </form>
        {erroTimes && (
          <p className="mensagem-erro" role="alert">
            {erroTimes}
          </p>
        )}
      </section>

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
