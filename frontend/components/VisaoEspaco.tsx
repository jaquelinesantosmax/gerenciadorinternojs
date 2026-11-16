"use client";

import { IconChartLine, IconLayoutKanban, IconList, IconLock, IconPlus, IconSearch, IconSettings, IconTimeline } from "@tabler/icons-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { EtiquetaPrioridade, EtiquetaStatus } from "@/components/EtiquetaStatus";
import { FormularioItem } from "@/components/FormularioItem";
import { Gantt } from "@/components/Gantt";
import { PlanejamentoScrum } from "@/components/PlanejamentoScrum";
import { QuadroKanban } from "@/components/QuadroKanban";
import { Relatorios } from "@/components/Relatorios";
import { AcessoNoTopo } from "./AcessoEspaco";
import { api, ErroApi, type EspacoDetalhe, type ItemLinha, type OpcoesItem, type QuadroResumo } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { MODELOS, NOME_PAPEL_ESPACO } from "@/lib/textos";

/** Itens de um espaço, ou só de um painel dele quando painelId vem preenchido. */
export function VisaoEspaco({ sigla, painelId }: { sigla: string; painelId?: string }) {
  const router = useRouter();
  const [espaco, setEspaco] = useState<EspacoDetalhe | null>(null);
  const [opcoes, setOpcoes] = useState<OpcoesItem | null>(null);
  const [itens, setItens] = useState<ItemLinha[] | null>(null);
  const [filtros, setFiltros] = useState({ busca: "", tipo_id: "", status_id: "", painel_id: painelId ?? "" });
  useEffect(() => setFiltros((f) => ({ ...f, painel_id: painelId ?? "" })), [painelId]);
  const [erro, setErro] = useState<string | null>(null);
  const [criando, setCriando] = useState(false);
  const [soBloqueados, setSoBloqueados] = useState(false);
  const [quadros, setQuadros] = useState<QuadroResumo[]>([]);
  const [quadroId, setQuadroId] = useState<string | null>(null);
  // A aba escolhida fica lembrada neste navegador, por espaço.
  const chaveAba = `gerenciador:aba:${sigla}`;
  const [aba, setAba] = useState<"lista" | "quadro" | "gantt" | "relatorios">("quadro");
  useEffect(() => {
    try {
      const salva = localStorage.getItem(chaveAba);
      if (salva === "lista" || salva === "quadro" || salva === "gantt" || salva === "relatorios") setAba(salva);
    } catch {
      /* navegador sem armazenamento: fica no padrão */
    }
  }, [chaveAba]);
  const mudarAba = (valor: "lista" | "quadro" | "gantt" | "relatorios") => {
    setAba(valor);
    try {
      localStorage.setItem(chaveAba, valor);
    } catch {
      /* ignora */
    }
  };
  const quadrosDoEspaco = quadros.filter((q) => q.painel_id === null);
  const quadroAtual = quadros.find((q) => q.id === quadroId);
  useEffect(() => {
    api
      .quadros(sigla)
      .then((lista) => {
        setQuadros(lista);
        const doPainel = painelId ? lista.find((q) => q.painel_id === painelId) : lista.find((q) => q.painel_id === null);
        setQuadroId(doPainel?.id ?? null);
      })
      .catch(() => setQuadros([]));
  }, [sigla, painelId]);

  useEffect(() => {
    setEspaco(null);
    api
      .espaco(sigla)
      .then(setEspaco)
      .catch((f) => setErro(f instanceof ErroApi ? f.message : "Não foi possível carregar."));
    api.opcoesItem(sigla).then(setOpcoes).catch(() => undefined);
  }, [sigla]);

  const carregar = useCallback(() => {
    api
      .itens(sigla, filtros)
      .then(setItens)
      .catch((f) => setErro(f instanceof ErroApi ? f.message : "Não foi possível carregar."));
  }, [sigla, filtros]);

  useEffect(() => {
    const espera = setTimeout(carregar, 200);
    return () => clearTimeout(espera);
  }, [carregar]);

  if (erro && !espaco) return <p className="mensagem-erro">{erro}</p>;
  if (!espaco) return <p className="legenda">Carregando…</p>;
  const painel = painelId ? espaco.paineis.find((p) => p.id === painelId) : undefined;
  if (painelId && !painel) return <p className="mensagem-erro">Painel não encontrado.</p>;

  const filtro = (campo: keyof typeof filtros, rotulo: string, lista: { id: string; nome: string }[]) => (
    <div style={{ minWidth: 150 }}>
      <label className="rotulo" htmlFor={`filtro-${campo}`}>
        {rotulo}
      </label>
      <select id={`filtro-${campo}`} className="campo" value={filtros[campo]} onChange={(e) => setFiltros({ ...filtros, [campo]: e.target.value })}>
        <option value="">Todos</option>
        {lista.map((o) => (
          <option key={o.id} value={o.id}>
            {o.nome}
          </option>
        ))}
      </select>
    </div>
  );

  const recarregarEspaco = () => void api.espaco(sigla).then(setEspaco).catch(() => router.replace("/"));

  return (
    <>
      <AcessoNoTopo espaco={espaco} parte="faixas" aoMudar={recarregarEspaco} />
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          {painel && (
            <nav className="legenda" style={{ marginBottom: 2 }}>
              <Link href={`/espacos/${espaco.sigla}`}>{espaco.nome}</Link> › Painel
            </nav>
          )}
          <h1 className="h1">{painel ? painel.nome : espaco.nome}</h1>
          <p className="legenda" style={{ margin: "4px 0 0" }}>
            {espaco.sigla} · {espaco.tipo === "pessoal" ? "Espaço pessoal" : `Espaço de projeto · modelo ${MODELOS[espaco.modelo ?? ""] ?? "—"}`} · você é{" "}
            {NOME_PAPEL_ESPACO[espaco.meu_papel]}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <AcessoNoTopo espaco={espaco} parte="botoes" aoMudar={recarregarEspaco} />
          {(espaco.permissoes.configurar || espaco.permissoes.gerenciar_membros) && (
            <Link className="botao" href={`/espacos/${espaco.sigla}/configuracoes`}>
              <IconSettings size={16} stroke={1.5} /> Configurações
            </Link>
          )}
          {espaco.permissoes.criar_itens && (
            <button className="botao botao-acao" onClick={() => setCriando(true)} disabled={!opcoes}>
              <IconPlus size={16} stroke={1.5} /> Criar item
            </button>
          )}
        </div>
      </div>

      <div role="tablist" aria-label="Visualização" style={{ display: "flex", gap: 4, marginTop: 14, alignItems: "center", flexWrap: "wrap" }}>
        {(
          [
            ["lista", "Lista", <IconList key="l" size={15} stroke={1.5} />],
            ["quadro", "Quadro", <IconLayoutKanban key="k" size={15} stroke={1.5} />],
            ["gantt", "Gantt", <IconTimeline key="g" size={15} stroke={1.5} />],
            ["relatorios", "Relatórios", <IconChartLine key="r" size={15} stroke={1.5} />],
          ] as const
        ).map(([valor, nome, icone]) => (
          <button key={valor} role="tab" aria-selected={aba === valor} className={`aba-visao${aba === valor ? " ativa" : ""}`} onClick={() => mudarAba(valor)}>
            {icone} {nome}
          </button>
        ))}
        {(aba === "quadro" || aba === "relatorios") && !painel && quadrosDoEspaco.length > 1 && (
          <select className="campo" aria-label="Quadro" style={{ width: "auto", height: 30, marginLeft: 8 }} value={quadroId ?? ""} onChange={(e) => setQuadroId(e.target.value)}>
            {quadrosDoEspaco.map((q) => (
              <option key={q.id} value={q.id}>
                {q.nome}
              </option>
            ))}
          </select>
        )}
      </div>

      {aba === "quadro" && (
        <div style={{ marginTop: 12 }}>
          {!quadroAtual ? (
            <p className="legenda">Carregando quadro…</p>
          ) : quadroAtual.tipo === "scrum" ? (
            <PlanejamentoScrum key={quadroAtual.id} quadroId={quadroAtual.id} podeMover={espaco.permissoes.editar_itens} />
          ) : (
            <QuadroKanban key={quadroAtual.id} quadroId={quadroAtual.id} podeMover={espaco.permissoes.editar_itens} />
          )}
        </div>
      )}
      {aba === "relatorios" && (
        <div style={{ marginTop: 12 }}>{quadroAtual ? <Relatorios key={quadroAtual.id} quadro={quadroAtual} /> : <p className="legenda">Carregando…</p>}</div>
      )}
      {aba === "gantt" && (
        <div style={{ marginTop: 12 }}>
          <Gantt sigla={espaco.sigla} painelId={painelId} />
        </div>
      )}

      {aba === "lista" && (
      <>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 12, alignItems: "flex-end" }}>
        <div style={{ position: "relative", flex: "1 1 220px", maxWidth: 320 }}>
          <label className="rotulo" htmlFor="filtro-busca">
            Buscar
          </label>
          <IconSearch size={16} stroke={1.5} style={{ position: "absolute", left: 10, top: 30, color: "var(--texto-2)" }} />
          <input id="filtro-busca" className="campo" style={{ paddingLeft: 32 }} placeholder="Resumo ou número" value={filtros.busca} onChange={(e) => setFiltros({ ...filtros, busca: e.target.value })} />
        </div>
        {filtro("tipo_id", "Tipo", espaco.tipos)}
        {filtro("status_id", "Status", espaco.status)}
        {espaco.paineis.length > 0 && !painel && filtro("painel_id", "Painel", espaco.paineis)}
        <label style={{ display: "flex", gap: 6, alignItems: "center", height: 36 }}>
          <input type="checkbox" checked={soBloqueados} onChange={(e) => setSoBloqueados(e.target.checked)} />
          Só bloqueados
        </label>
      </div>

      <div className="painel" style={{ marginTop: 14, padding: "4px 8px", overflowX: "auto" }}>
        {itens === null ? (
          <p className="legenda" style={{ padding: 10 }}>
            Carregando…
          </p>
        ) : itens.length === 0 ? (
          <p className="legenda" style={{ padding: 10 }}>
            {Object.values(filtros).some(Boolean) ? "Nenhum item com esses filtros." : "Nenhum item ainda."}
          </p>
        ) : (
          <table className="tabela">
            <thead>
              <tr>
                <th style={{ width: 90 }}>Chave</th>
                <th>Resumo</th>
                <th style={{ width: 100 }}>Tipo</th>
                <th style={{ width: 140 }}>Status</th>
                <th style={{ width: 90 }}>Prioridade</th>
                <th style={{ width: 150 }}>Responsável</th>
                <th style={{ width: 96 }}>Entrega</th>
                {espaco.paineis.length > 0 && <th style={{ width: 130 }}>Painel</th>}
                <th style={{ width: 130 }}>Bloqueado por</th>
              </tr>
            </thead>
            <tbody>
              {itens.filter((i) => !soBloqueados || i.bloqueado_por.length > 0).map((i) => (
                <tr key={i.id} className="clicavel" tabIndex={0} onClick={() => router.push(`/itens/${i.chave}`)} onKeyDown={(e) => e.key === "Enter" && router.push(`/itens/${i.chave}`)}>
                  <td className="legenda" style={{ fontWeight: 400 }}>
                    {i.chave}
                  </td>
                  <td style={{ fontWeight: i.nivel === "epico" ? 500 : 400 }}>{i.resumo}</td>
                  <td className="legenda">{i.tipo.nome}</td>
                  <td>
                    <EtiquetaStatus nome={i.status.nome} categoria={i.status.categoria} />
                  </td>
                  <td>
                    <EtiquetaPrioridade prioridade={i.prioridade} />
                  </td>
                  <td>{i.responsavel?.nome ?? "—"}</td>
                  <td className="legenda" style={{ fontVariantNumeric: "tabular-nums" }}>
                    {formatarData(`${i.data_entrega}T12:00:00Z`)}
                  </td>
                  {espaco.paineis.length > 0 && <td className="legenda">{i.painel?.nome ?? "—"}</td>}
                  <td>
                    {i.bloqueado_por.length ? (
                      <span className="etiqueta etiqueta-alerta" style={{ whiteSpace: "normal" }}>
                        <IconLock size={12} stroke={1.5} /> {i.bloqueado_por.join(", ")}
                      </span>
                    ) : (
                      <span className="legenda">—</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      </>
      )}
      <style>{`
        .aba-visao{display:inline-flex;gap:6px;align-items:center;border:none;background:none;font-size:13px;color:var(--texto-2);padding:6px 12px;border-radius:20px;cursor:pointer}
        .aba-visao:hover{background:#fff}
        .aba-visao.ativa{background:var(--verde-fundo);color:var(--verde-escuro);font-weight:500}
      `}</style>

      {criando && opcoes && (
        <div className="fundo-janela" onMouseDown={(e) => e.target === e.currentTarget && setCriando(false)}>
          <div className="janela" role="dialog" aria-modal="true" aria-labelledby="titulo-criar">
            <h2 id="titulo-criar" className="h2" style={{ marginBottom: 14 }}>
              Criar item em {espaco.nome}
            </h2>
            {opcoes.times.length === 0 ? (
              <p className="caixa-alerta">Ainda não há Times cadastrados. Peça ao ADM da plataforma para cadastrar a lista de Times.</p>
            ) : (
              <FormularioItem
                painelInicial={painelId}
                espaco={espaco}
                opcoes={opcoes}
                aoCancelar={() => setCriando(false)}
                aoSalvar={async (dados) => {
                  const novo = await api.criarItem(espaco.sigla, dados);
                  router.push(`/itens/${novo.chave}`);
                }}
              />
            )}
          </div>
        </div>
      )}
    </>
  );
}
