"use client";

import { IconPencil, IconTrash } from "@tabler/icons-react";
import { useCallback, useEffect, useState } from "react";
import { Avatar } from "@/components/Avatar";
import { BuscaPessoa } from "@/components/BuscaPessoa";
import { api, ErroApi, type TimeDetalhe } from "@/lib/api";

const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);

/** Cadastro de Times: quem está em cada time. Um time pode receber acesso a espaços (nas configurações do espaço). */
export default function PaginaTimes() {
  const [dados, setDados] = useState<{ pode_criar: boolean; times: TimeDetalhe[] } | null>(null);
  const [novo, setNovo] = useState("");
  const [aberto, setAberto] = useState<string | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      setDados(await api.gestaoTimes());
    } catch (f) {
      setErro(msg(f, "Não foi possível carregar os times."));
    }
  }, []);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const executar = async (acao: () => Promise<unknown>) => {
    setErro(null);
    try {
      await acao();
      await carregar();
      return true;
    } catch (f) {
      setErro(msg(f, "Não foi possível concluir."));
      return false;
    }
  };

  if (!dados) return <p className="legenda">{erro ?? "Carregando…"}</p>;

  return (
    <div style={{ maxWidth: 820 }}>
      <h1 className="h1">Times</h1>
      <p className="legenda" style={{ margin: "4px 0 0" }}>
        O time aparece no campo Time dos itens e pode receber acesso a espaços: quem entra no time ganha o acesso, quem sai perde. Criam
        times o ADM da plataforma, o Gestor, quem pode criar espaços e o ADM de algum espaço. Mudam o time quem o criou, o Gestor e o ADM
        da plataforma.
      </p>

      {dados.pode_criar && (
        <form
          className="painel"
          style={{ display: "flex", gap: 8, marginTop: 16 }}
          onSubmit={async (e) => {
            e.preventDefault();
            if (await executar(() => api.criarTime(novo))) setNovo("");
          }}
        >
          <input className="campo" aria-label="Nome do novo time" placeholder="Nome do time (ex.: Legal Ops)" value={novo} onChange={(e) => setNovo(e.target.value)} />
          <button className="botao botao-acao" type="submit" disabled={!novo.trim()}>
            Criar time
          </button>
        </form>
      )}
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}

      <ul style={{ listStyle: "none", padding: 0, margin: "16px 0 0", display: "grid", gap: 10 }}>
        {dados.times.map((t) => (
          <li key={t.id} className="painel" style={{ opacity: t.ativo ? 1 : 0.6 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <button
                className="botao-texto"
                aria-expanded={aberto === t.id}
                onClick={() => setAberto(aberto === t.id ? null : t.id)}
                style={{ flex: 1, textAlign: "left" }}
              >
                <span className="h3" style={{ fontSize: 14 }}>
                  {t.nome}
                </span>{" "}
                {!t.ativo && <span className="etiqueta etiqueta-neutra">Desativado</span>}
                <span className="legenda">
                  {" "}
                  · {t.membros.length === 1 ? "1 pessoa" : `${t.membros.length} pessoas`}
                  {t.criado_por && ` · criado por ${t.criado_por.nome}`}
                </span>
              </button>
              {t.pode_editar && (
                <>
                  <button
                    className="botao botao-discreto"
                    aria-label={`Renomear ${t.nome}`}
                    onClick={() => {
                      const nome = window.prompt("Novo nome do time", t.nome);
                      if (nome && nome !== t.nome) void executar(() => api.alterarTime(t.id, { nome }));
                    }}
                  >
                    <IconPencil size={14} stroke={1.5} />
                  </button>
                  <button className="botao botao-discreto" onClick={() => void executar(() => api.alterarTime(t.id, { ativo: !t.ativo }))}>
                    {t.ativo ? "Desativar" : "Reativar"}
                  </button>
                </>
              )}
            </div>
            {aberto === t.id && (
              <div style={{ marginTop: 10 }}>
                <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                  {t.membros.map((p) => (
                    <li key={p.id} style={{ display: "flex", alignItems: "center", gap: 10, padding: "6px 0", borderBottom: "0.5px solid var(--borda)" }}>
                      <Avatar nome={p.nome} fotoUrl={p.foto_url} />
                      <div style={{ flex: 1 }}>
                        <div>{p.nome}</div>
                        <div className="legenda">{p.email}</div>
                      </div>
                      {t.pode_editar && (
                        <button className="botao botao-discreto" aria-label={`Tirar ${p.nome} do time`} onClick={() => void executar(() => api.tirarDoTime(t.id, p.id))}>
                          <IconTrash size={14} stroke={1.5} />
                        </button>
                      )}
                    </li>
                  ))}
                  {t.membros.length === 0 && <li className="legenda">Ninguém no time ainda.</li>}
                </ul>
                {t.pode_editar && (
                  <div style={{ marginTop: 10 }}>
                    <BuscaPessoa
                      rotulo={`Colocar pessoa no time ${t.nome}`}
                      jaEscolhidas={new Set(t.membros.map((p) => p.id))}
                      textoJaEscolhida="já está no time"
                      aoEscolher={(p) => void executar(() => api.adicionarAoTime(t.id, p.id))}
                    />
                  </div>
                )}
              </div>
            )}
          </li>
        ))}
        {dados.times.length === 0 && <li className="legenda">Nenhum time ainda. Sem times, ninguém consegue criar itens.</li>}
      </ul>
    </div>
  );
}
