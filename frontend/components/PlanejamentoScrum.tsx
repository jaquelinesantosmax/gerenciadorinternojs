"use client";

import { IconPlayerPlay, IconPlus, IconTrash, IconX } from "@tabler/icons-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, ErroApi, type Card, type Planejamento, type Sprint } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { Dialogo } from "./Dialogo";
import { EtiquetaPrioridade, EtiquetaStatus } from "./EtiquetaStatus";
import { QuadroKanban } from "./QuadroKanban";

const msg = (f: unknown, padrao: string) => (f instanceof ErroApi ? f.message : padrao);
const data = (d: string | null) => (d ? formatarData(`${d}T12:00:00Z`) : "—");
const hoje = () => new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10);
const daqui = (dias: number) => new Date(Date.now() - 3 * 3600 * 1000 + dias * 86400000).toISOString().slice(0, 10);

/** Valor do card na unidade do quadro (pontos, horas ou 1 por item). */
export function valorDoCard(card: Card, unidade: string): number {
  if (unidade === "itens") return 1;
  return Number((unidade === "horas" ? card.estimativa_horas : card.estimativa) ?? 0);
}

export function formatarValor(n: number | string | null | undefined, unidade: string): string {
  const v = Number(n ?? 0);
  const texto = v.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
  return unidade === "pontos" ? `${texto} pts` : unidade === "horas" ? `${texto} h` : `${texto} ${v === 1 ? "item" : "itens"}`;
}

function LinhaItem({ card, unidade, acao }: { card: Card; unidade: string; acao?: React.ReactNode }) {
  return (
    <li className="linha-scrum">
      <Link href={`/itens/${card.chave}`} className="legenda" style={{ minWidth: 64 }}>
        {card.chave}
      </Link>
      <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{card.resumo}</span>
      <EtiquetaPrioridade prioridade={card.prioridade} />
      <EtiquetaStatus nome={card.status} categoria={card.status_categoria} />
      <span className="legenda" style={{ width: 64, textAlign: "right", fontVariantNumeric: "tabular-nums" }}>
        {unidade === "itens" ? "" : formatarValor(valorDoCard(card, unidade), unidade)}
      </span>
      {acao}
    </li>
  );
}

/** Quadro Scrum: backlog, sprints (várias ativas ao mesmo tempo) e o quadro de cada sprint ativa. */
export function PlanejamentoScrum({ quadroId, podeMover }: { quadroId: string; podeMover: boolean }) {
  const [plano, setPlano] = useState<Planejamento | null>(null);
  const [vendo, setVendo] = useState<string>("planejamento");
  const [erro, setErro] = useState<string | null>(null);
  const [iniciar, setIniciar] = useState<{ sprint: Sprint; inicio: string; fim: string } | null>(null);
  const [encerrar, setEncerrar] = useState<{ sprint: Sprint; destino: string } | null>(null);
  const [editando, setEditando] = useState<{ id: string; nome: string; objetivo: string } | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const carregar = useCallback(async () => {
    try {
      setPlano(await api.planejamento(quadroId));
    } catch (f) {
      setErro(msg(f, "Não foi possível carregar."));
    }
  }, [quadroId]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  const executar = async (acao: () => Promise<unknown>) => {
    setErro(null);
    setOcupado(true);
    try {
      await acao();
      await carregar();
      return true;
    } catch (f) {
      setErro(msg(f, "Não foi possível concluir."));
      return false;
    } finally {
      setOcupado(false);
    }
  };

  if (!plano) return <p className="legenda">{erro ?? "Carregando…"}</p>;
  const ativas = plano.sprints.filter((s) => s.estado === "ativa");
  const abertas = plano.sprints;
  const u = plano.unidade;
  const sprintVista = ativas.find((s) => s.id === vendo);

  return (
    <div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", marginBottom: 12 }}>
        <button className={`aba-pequena${vendo === "planejamento" ? " ativa" : ""}`} onClick={() => setVendo("planejamento")}>
          Backlog e sprints
        </button>
        {ativas.map((s) => (
          <button key={s.id} className={`aba-pequena${vendo === s.id ? " ativa" : ""}`} onClick={() => setVendo(s.id)}>
            Quadro da {s.nome}
          </button>
        ))}
        <span className="legenda" style={{ marginLeft: "auto" }}>
          Estimativa em {plano.nome_unidade.toLowerCase()}
        </span>
      </div>
      {erro && (
        <p className="caixa-alerta" role="alert" style={{ marginTop: 0 }}>
          {erro}
        </p>
      )}

      {sprintVista ? (
        <div>
          <p className="legenda" style={{ marginTop: 0 }}>
            {data(sprintVista.inicio)} a {data(sprintVista.fim)}
            {sprintVista.objetivo ? ` · Objetivo: ${sprintVista.objetivo}` : ""}
          </p>
          <QuadroKanban key={sprintVista.id} quadroId={quadroId} sprintId={sprintVista.id} podeMover={podeMover} />
        </div>
      ) : (
        <>
          {abertas.map((s) => (
            <section key={s.id} className="painel bloco-sprint" aria-label={s.nome}>
              <header>
                <div style={{ flex: 1, minWidth: 0 }}>
                  {editando?.id === s.id ? (
                    <div style={{ display: "grid", gap: 6 }}>
                      <input className="campo" aria-label="Nome da sprint" value={editando.nome} onChange={(e) => setEditando({ ...editando, nome: e.target.value })} />
                      <input className="campo" aria-label="Objetivo da sprint" placeholder="Objetivo" value={editando.objetivo} onChange={(e) => setEditando({ ...editando, objetivo: e.target.value })} />
                      <div style={{ display: "flex", gap: 6 }}>
                        <button className="botao botao-acao" onClick={async () => (await executar(() => api.editarSprint(s.id, { nome: editando.nome, objetivo: editando.objetivo }))) && setEditando(null)}>
                          Salvar
                        </button>
                        <button className="botao" onClick={() => setEditando(null)}>
                          Cancelar
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                        <h3 className="h3" style={{ margin: 0 }}>
                          {s.nome}
                        </h3>
                        <span className={`etiqueta ${s.estado === "ativa" ? "status-em_andamento" : "etiqueta-neutra"}`}>{s.estado === "ativa" ? "Ativa" : "Planejada"}</span>
                        <span className="legenda">
                          {s.inicio || s.fim ? `${data(s.inicio)} a ${data(s.fim)} · ` : ""}
                          {s.itens.length} item(ns) · {formatarValor(s.total, u)}
                          {s.estado === "ativa" && s.compromisso !== null ? ` (compromisso no início: ${formatarValor(s.compromisso, u)})` : ""}
                        </span>
                      </div>
                      {s.objetivo && <div className="legenda" style={{ marginTop: 2 }}>Objetivo: {s.objetivo}</div>}
                    </>
                  )}
                </div>
                {plano.pode_gerenciar && editando?.id !== s.id && (
                  <div style={{ display: "flex", gap: 6, flexShrink: 0 }}>
                    <button className="botao botao-discreto" onClick={() => setEditando({ id: s.id, nome: s.nome, objetivo: s.objetivo ?? "" })}>
                      Editar
                    </button>
                    {s.estado === "planejada" ? (
                      <>
                        <button className="botao botao-acao" onClick={() => setIniciar({ sprint: s, inicio: s.inicio ?? hoje(), fim: s.fim ?? daqui(14) })}>
                          <IconPlayerPlay size={14} stroke={1.5} /> Iniciar
                        </button>
                        <button className="botao botao-discreto" aria-label={`Excluir ${s.nome}`} onClick={() => void executar(() => api.excluirSprint(s.id))}>
                          <IconTrash size={14} stroke={1.5} />
                        </button>
                      </>
                    ) : (
                      <button className="botao" onClick={() => setEncerrar({ sprint: s, destino: "backlog" })}>
                        Encerrar sprint
                      </button>
                    )}
                  </div>
                )}
              </header>
              <ul className="lista-scrum">
                {s.itens.map((c) => (
                  <LinhaItem
                    key={c.chave}
                    card={c}
                    unidade={u}
                    acao={
                      plano.pode_gerenciar && (
                        <button className="botao botao-discreto" aria-label={`Tirar ${c.chave} da sprint`} title="Voltar para o backlog" onClick={() => void executar(() => api.tirarDaSprint(s.id, c.chave))}>
                          <IconX size={14} stroke={1.5} />
                        </button>
                      )
                    }
                  />
                ))}
                {s.itens.length === 0 && <li className="legenda">Nenhum item. Adicione pelo backlog abaixo.</li>}
              </ul>
            </section>
          ))}

          {plano.pode_gerenciar && (
            <button className="botao" style={{ marginTop: 10 }} disabled={ocupado} onClick={() => void executar(() => api.criarSprint(quadroId))}>
              <IconPlus size={14} stroke={1.5} /> Nova sprint
            </button>
          )}

          <section className="painel bloco-sprint" aria-label="Backlog" style={{ marginTop: 14 }}>
            <header>
              <h3 className="h3" style={{ margin: 0, flex: 1 }}>
                Backlog <span className="legenda">· {plano.backlog.length} item(ns) · {formatarValor(plano.backlog_total, u)}</span>
              </h3>
            </header>
            <ul className="lista-scrum">
              {plano.backlog.map((c) => (
                <LinhaItem
                  key={c.chave}
                  card={c}
                  unidade={u}
                  acao={
                    plano.pode_gerenciar && abertas.length > 0 && (
                      <select
                        className="campo"
                        style={{ width: 150, height: 30, fontSize: 12 }}
                        aria-label={`Mandar ${c.chave} para uma sprint`}
                        value=""
                        onChange={(e) => e.target.value && void executar(() => api.adicionarNaSprint(e.target.value, c.chave))}
                      >
                        <option value="">Mandar para…</option>
                        {abertas.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.nome}
                          </option>
                        ))}
                      </select>
                    )
                  }
                />
              ))}
              {plano.backlog.length === 0 && <li className="legenda">Backlog vazio.</li>}
            </ul>
            {abertas.length === 0 && plano.pode_gerenciar && <p className="legenda">Crie uma sprint para começar a planejar.</p>}
          </section>
        </>
      )}

      <Dialogo
        aberto={iniciar !== null}
        titulo={`Iniciar ${iniciar?.sprint.nome ?? ""}?`}
        textoConfirmar="Iniciar sprint"
        ocupado={ocupado}
        aoConfirmar={async () => {
          if (iniciar && (await executar(() => api.iniciarSprint(iniciar.sprint.id, iniciar.inicio, iniciar.fim)))) setIniciar(null);
        }}
        aoCancelar={() => setIniciar(null)}
      >
        {iniciar && (
          <div className="grade-campos">
            <div>
              <label className="rotulo" htmlFor="sprint-inicio">
                Início
              </label>
              <input id="sprint-inicio" type="date" className="campo" value={iniciar.inicio} onChange={(e) => setIniciar({ ...iniciar, inicio: e.target.value })} />
            </div>
            <div>
              <label className="rotulo" htmlFor="sprint-fim">
                Fim
              </label>
              <input id="sprint-fim" type="date" className="campo" value={iniciar.fim} onChange={(e) => setIniciar({ ...iniciar, fim: e.target.value })} />
            </div>
            <p className="legenda" style={{ gridColumn: "1 / -1", margin: 0 }}>
              O total dos itens agora ({formatarValor(iniciar.sprint.total, u)}) vira o compromisso da sprint, base do burndown e da velocidade.
            </p>
          </div>
        )}
      </Dialogo>

      <Dialogo
        aberto={encerrar !== null}
        titulo={`Encerrar ${encerrar?.sprint.nome ?? ""}?`}
        textoConfirmar="Encerrar sprint"
        ocupado={ocupado}
        aoConfirmar={async () => {
          if (encerrar && (await executar(() => api.encerrarSprint(encerrar.sprint.id, encerrar.destino)))) {
            setEncerrar(null);
            setVendo("planejamento");
          }
        }}
        aoCancelar={() => setEncerrar(null)}
      >
        {encerrar && (
          <>
            <p style={{ margin: "0 0 8px" }}>
              {encerrar.sprint.itens.filter((c) => c.status_categoria !== "concluido").length} item(ns) não concluído(s). Para onde eles vão?
            </p>
            <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <input type="radio" name="destino" checked={encerrar.destino === "backlog"} onChange={() => setEncerrar({ ...encerrar, destino: "backlog" })} />
              De volta ao backlog
            </label>
            <label style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
              <input type="radio" name="destino" checked={encerrar.destino === "nova"} onChange={() => setEncerrar({ ...encerrar, destino: "nova" })} />
              Para uma sprint nova
            </label>
            {abertas
              .filter((s) => s.id !== encerrar.sprint.id)
              .map((s) => (
                <label key={s.id} style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 4 }}>
                  <input type="radio" name="destino" checked={encerrar.destino === s.id} onChange={() => setEncerrar({ ...encerrar, destino: s.id })} />
                  Para a {s.nome}
                </label>
              ))}
          </>
        )}
      </Dialogo>

      <style>{`
        .bloco-sprint{margin-top:10px;padding:12px 14px}
        .bloco-sprint header{display:flex;gap:10px;align-items:flex-start;margin-bottom:6px}
        .lista-scrum{list-style:none;padding:0;margin:0}
        .linha-scrum{display:flex;gap:8px;align-items:center;padding:6px 0;border-bottom:0.5px solid var(--borda);font-size:13px}
        .linha-scrum:last-child{border-bottom:none}
        .aba-pequena{border:0.5px solid var(--borda);background:#fff;border-radius:20px;padding:4px 12px;font-size:12px;cursor:pointer}
        .aba-pequena.ativa{background:var(--verde-fundo);border-color:var(--verde);color:var(--verde-escuro)}
      `}</style>
    </div>
  );
}
