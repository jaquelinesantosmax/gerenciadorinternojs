"use client";

import { IconPlus, IconSearch, IconSettings } from "@tabler/icons-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { EtiquetaPrioridade, EtiquetaStatus } from "@/components/EtiquetaStatus";
import { FormularioItem } from "@/components/FormularioItem";
import { api, ErroApi, type EspacoDetalhe, type ItemLinha, type OpcoesItem } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { MODELOS, NOME_PAPEL_ESPACO } from "@/lib/textos";

export default function PaginaEspaco() {
  const { sigla } = useParams<{ sigla: string }>();
  const router = useRouter();
  const [espaco, setEspaco] = useState<EspacoDetalhe | null>(null);
  const [opcoes, setOpcoes] = useState<OpcoesItem | null>(null);
  const [itens, setItens] = useState<ItemLinha[] | null>(null);
  const [filtros, setFiltros] = useState({ busca: "", tipo_id: "", status_id: "", painel_id: "" });
  const [erro, setErro] = useState<string | null>(null);
  const [criando, setCriando] = useState(false);

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

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h1 className="h1">{espaco.nome}</h1>
          <p className="legenda" style={{ margin: "4px 0 0" }}>
            {espaco.sigla} · {espaco.tipo === "pessoal" ? "Espaço pessoal" : `Espaço de projeto · modelo ${MODELOS[espaco.modelo ?? ""] ?? "—"}`} · você é{" "}
            {NOME_PAPEL_ESPACO[espaco.meu_papel]}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
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

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 16, alignItems: "flex-end" }}>
        <div style={{ position: "relative", flex: "1 1 220px", maxWidth: 320 }}>
          <label className="rotulo" htmlFor="filtro-busca">
            Buscar
          </label>
          <IconSearch size={16} stroke={1.5} style={{ position: "absolute", left: 10, top: 30, color: "var(--texto-2)" }} />
          <input id="filtro-busca" className="campo" style={{ paddingLeft: 32 }} placeholder="Resumo ou número" value={filtros.busca} onChange={(e) => setFiltros({ ...filtros, busca: e.target.value })} />
        </div>
        {filtro("tipo_id", "Tipo", espaco.tipos)}
        {filtro("status_id", "Status", espaco.status)}
        {espaco.paineis.length > 0 && filtro("painel_id", "Painel", espaco.paineis)}
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
              </tr>
            </thead>
            <tbody>
              {itens.map((i) => (
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
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

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
