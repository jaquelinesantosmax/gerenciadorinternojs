"use client";

import { useEffect, useMemo, useState } from "react";
import { api, ErroApi, type DadosItem, type DocTexto, type EspacoDetalhe, type ItemDetalhe, type ItemLinha, type OpcoesItem } from "@/lib/api";
import { ORDEM_PRIORIDADES, PRIORIDADES } from "@/lib/textos";
import { EntradaCampo } from "./CampoPersonalizado";
import { Editor } from "./Editor";
import { useEu } from "./Moldura";

const hoje = () => new Date(Date.now() - 3 * 3600 * 1000).toISOString().slice(0, 10);

/** Formulário de criação e edição de item, com os campos padronizados e os personalizados do tipo. */
export function FormularioItem({
  espaco,
  opcoes,
  inicial,
  aoSalvar,
  aoCancelar,
  painelInicial,
}: {
  painelInicial?: string;
  espaco: EspacoDetalhe;
  opcoes: OpcoesItem;
  inicial?: ItemDetalhe | null;
  aoSalvar: (dados: DadosItem) => Promise<void>;
  aoCancelar: () => void;
}) {
  const { eu } = useEu();
  const editando = Boolean(inicial);
  const statusInicial = espaco.status.find((s) => s.nome === "A fazer")?.id ?? espaco.status[0]?.id;
  const tipoInicial = espaco.tipos.find((t) => t.nome === "Tarefa")?.id ?? espaco.tipos[0]?.id;
  const [d, setD] = useState<Record<string, unknown>>(() =>
    inicial
      ? {
          tipo_id: inicial.tipo.id,
          resumo: inicial.resumo,
          status_id: inicial.status.id,
          prioridade: inicial.prioridade,
          responsavel_id: inicial.responsavel?.id ?? "",
          time_id: inicial.time.id,
          data_inicio: inicial.data_inicio,
          data_entrega: inicial.data_entrega,
          data_real_entrega: inicial.data_real_entrega ?? "",
          justificativa_atraso: inicial.justificativa_atraso ?? "",
          estimativa: inicial.estimativa ?? "",
          painel_id: inicial.painel?.id ?? "",
          origem_id: inicial.origem?.id ?? "",
          pai_id: "",
          categorias: inicial.categorias,
          co_responsaveis: inicial.co_responsaveis.map((p) => p.id),
          valores: { ...inicial.valores },
        }
      : {
          tipo_id: tipoInicial,
          resumo: "",
          status_id: statusInicial,
          prioridade: "",
          responsavel_id: opcoes.responsaveis.some((p) => p.id === eu.id) ? eu.id : "",
          time_id: "",
          data_inicio: hoje(),
          data_entrega: "",
          painel_id: painelInicial ?? (espaco.paineis.length === 1 ? espaco.paineis[0].id : ""),
          categorias: [],
          co_responsaveis: [],
          valores: {},
        },
  );
  const [descricao, setDescricao] = useState<DocTexto | null>(null);
  const [itens, setItens] = useState<ItemLinha[]>([]);
  const [paiChave, setPaiChave] = useState<string>(inicial?.pai?.chave ?? "");
  const [novaCategoria, setNovaCategoria] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    api.itens(espaco.sigla).then(setItens).catch(() => setItens([]));
  }, [espaco.sigla]);

  const tipo = espaco.tipos.find((t) => t.id === d.tipo_id);
  const camposDoTipo = opcoes.campos.filter((c) => tipo && c.tipos_item.includes(tipo.id));
  const paisPossiveis = useMemo(() => {
    const nivelPai = tipo?.nivel === "padrao" ? "epico" : tipo?.nivel === "subtarefa" ? "padrao" : null;
    return nivelPai ? itens.filter((i) => i.nivel === nivelPai && i.chave !== inicial?.chave) : [];
  }, [itens, tipo, inicial?.chave]);
  const atrasado = Boolean(d.data_real_entrega && d.data_entrega && String(d.data_real_entrega) > String(d.data_entrega));
  const mudar = (campo: string, valor: unknown) => setD((atual) => ({ ...atual, [campo]: valor }));
  const valores = (d.valores as Record<string, unknown>) ?? {};
  const categorias = (d.categorias as string[]) ?? [];

  function adicionarCategoria() {
    const nova = novaCategoria.trim();
    if (nova && !categorias.some((c) => c.toLowerCase() === nova.toLowerCase())) mudar("categorias", [...categorias, nova]);
    setNovaCategoria("");
  }

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    const pai = paisPossiveis.find((i) => i.chave === paiChave);
    const dados: DadosItem = {
      ...d,
      pai_id: tipo?.nivel === "epico" ? null : pai?.id ?? null,
      painel_id: d.painel_id || null,
      origem_id: d.origem_id || null,
      data_real_entrega: d.data_real_entrega || null,
      justificativa_atraso: d.justificativa_atraso || null,
      estimativa: d.estimativa === "" ? null : d.estimativa,
      valores: Object.fromEntries(Object.entries(valores).filter(([cid]) => camposDoTipo.some((c) => c.id === cid))),
    };
    // Se a lista de itens ainda não carregou, o pai atual é mantido (não some sem querer).
    if (!pai && paiChave && paiChave === inicial?.pai?.chave) delete dados.pai_id;
    if (!editando && descricao) dados.descricao = descricao;
    setOcupado(true);
    try {
      await aoSalvar(dados);
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível salvar.");
      setOcupado(false);
    }
  }

  const sel = (campo: string, rotulo: string, lista: { id: string; nome: string }[], obrigatorio = true, vazio = "Escolha") => (
    <div>
      <label className={`rotulo${obrigatorio ? " obrigatorio" : ""}`} htmlFor={`f-${campo}`}>
        {rotulo}
      </label>
      <select id={`f-${campo}`} className="campo" value={String(d[campo] ?? "")} onChange={(e) => mudar(campo, e.target.value)}>
        <option value="">{vazio}</option>
        {lista.map((o) => (
          <option key={o.id} value={o.id}>
            {o.nome}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <form onSubmit={enviar} noValidate>
      <div className="grade-campos">
        {sel("tipo_id", "Tipo", espaco.tipos)}
        <div style={{ gridColumn: "1 / -1" }}>
          <label className="rotulo obrigatorio" htmlFor="f-resumo">
            Resumo
          </label>
          <input id="f-resumo" className="campo" maxLength={255} value={String(d.resumo ?? "")} onChange={(e) => mudar("resumo", e.target.value)} autoFocus />
        </div>
        {sel("status_id", "Status", espaco.status)}
        {sel("prioridade", "Prioridade", ORDEM_PRIORIDADES.map((p) => ({ id: p, nome: PRIORIDADES[p] })))}
        {sel("responsavel_id", "Responsável", opcoes.responsaveis.map((p) => ({ id: p.id, nome: p.nome })))}
        {sel("time_id", "Time", opcoes.times.concat(inicial && !opcoes.times.some((t) => t.id === inicial.time.id) ? [inicial.time] : []))}
        <div>
          <label className="rotulo obrigatorio" htmlFor="f-inicio">
            Data de início
          </label>
          <input id="f-inicio" type="date" className="campo" value={String(d.data_inicio ?? "")} onChange={(e) => mudar("data_inicio", e.target.value)} />
        </div>
        <div>
          <label className="rotulo obrigatorio" htmlFor="f-entrega">
            Data de entrega
          </label>
          <input id="f-entrega" type="date" className="campo" value={String(d.data_entrega ?? "")} onChange={(e) => mudar("data_entrega", e.target.value)} />
        </div>
        {espaco.paineis.length > 0 && sel("painel_id", "Painel", espaco.paineis)}
        {tipo && tipo.nivel !== "epico" && (
          <div>
            <label className={`rotulo${tipo.nivel === "subtarefa" ? " obrigatorio" : ""}`} htmlFor="f-pai">
              {tipo.nivel === "subtarefa" ? "Item pai" : "Épico (pai)"}
            </label>
            <select id="f-pai" className="campo" value={paiChave} onChange={(e) => setPaiChave(e.target.value)}>
              <option value="">{tipo.nivel === "subtarefa" ? "Escolha" : "Sem épico"}</option>
              {paisPossiveis.map((i) => (
                <option key={i.id} value={i.chave}>
                  {i.chave} · {i.resumo}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <details style={{ marginTop: 16 }} open={editando}>
        <summary className="h3" style={{ cursor: "pointer" }}>
          Campos opcionais{camposDoTipo.length ? " e personalizados" : ""}
        </summary>
        <div className="grade-campos" style={{ marginTop: 10 }}>
          {espaco.origens.length > 0 && sel("origem_id", "Origem da solicitação", espaco.origens.concat(inicial?.origem && !espaco.origens.some((o) => o.id === inicial.origem?.id) ? [inicial.origem] : []), false, "—")}
          <div>
            <label className="rotulo" htmlFor="f-estimativa">
              Estimativa (story points)
            </label>
            <input id="f-estimativa" type="number" min={0} step="0.5" className="campo" value={String(d.estimativa ?? "")} onChange={(e) => mudar("estimativa", e.target.value)} />
          </div>
          <div>
            <label className="rotulo" htmlFor="f-real">
              Data real da entrega
            </label>
            <input id="f-real" type="date" className="campo" value={String(d.data_real_entrega ?? "")} onChange={(e) => mudar("data_real_entrega", e.target.value)} />
          </div>
          {(atrasado || Boolean(d.justificativa_atraso)) && (
            <div style={{ gridColumn: "1 / -1" }}>
              <label className={`rotulo${atrasado ? " obrigatorio" : ""}`} htmlFor="f-justificativa">
                Justificativa do atraso
              </label>
              <textarea id="f-justificativa" className="campo" value={String(d.justificativa_atraso ?? "")} onChange={(e) => mudar("justificativa_atraso", e.target.value)} />
            </div>
          )}
          <fieldset style={{ border: "none", padding: 0, margin: 0, gridColumn: "1 / -1" }}>
            <legend className="rotulo">Co-responsáveis</legend>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 14px" }}>
              {opcoes.responsaveis
                .filter((p) => p.id !== d.responsavel_id)
                .map((p) => {
                  const lista = (d.co_responsaveis as string[]) ?? [];
                  return (
                    <label key={p.id} style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                      <input type="checkbox" checked={lista.includes(p.id)} onChange={(e) => mudar("co_responsaveis", e.target.checked ? [...lista, p.id] : lista.filter((x) => x !== p.id))} />
                      {p.nome}
                    </label>
                  );
                })}
              {opcoes.responsaveis.length <= 1 && <span className="legenda">Só há uma pessoa que pode ser responsável neste espaço.</span>}
            </div>
          </fieldset>
          <div style={{ gridColumn: "1 / -1" }}>
            <label className="rotulo" htmlFor="f-categoria">
              Categorias
            </label>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: categorias.length ? 6 : 0 }}>
              {categorias.map((c) => (
                <span key={c} className="etiqueta etiqueta-neutra">
                  {c}
                  <button type="button" aria-label={`Tirar ${c}`} onClick={() => mudar("categorias", categorias.filter((x) => x !== c))} style={{ border: "none", background: "none", cursor: "pointer", padding: 0, color: "inherit" }}>
                    ×
                  </button>
                </span>
              ))}
            </div>
            <input
              id="f-categoria"
              className="campo"
              list="sugestoes-categorias"
              placeholder="Digite e tecle Enter"
              value={novaCategoria}
              onChange={(e) => setNovaCategoria(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === ",") {
                  e.preventDefault();
                  adicionarCategoria();
                }
              }}
              onBlur={adicionarCategoria}
            />
            <datalist id="sugestoes-categorias">
              {opcoes.categorias.filter((c) => !categorias.includes(c)).map((c) => (
                <option key={c} value={c} />
              ))}
            </datalist>
          </div>
          {camposDoTipo.map((campo) => (
            <EntradaCampo
              key={campo.id}
              campo={campo}
              valor={valores[campo.id]}
              aoMudar={(v) => mudar("valores", { ...valores, [campo.id]: v })}
              membros={opcoes.membros}
              moedas={opcoes.moedas}
            />
          ))}
        </div>
      </details>

      {!editando && (
        <div style={{ marginTop: 16 }}>
          <span className="rotulo">Descrição</span>
          <Editor rotulo="Descrição" valor={null} aoMudar={setDescricao} pessoas={opcoes.membros} />
          <p className="legenda" style={{ margin: "4px 0 0" }}>
            Imagens e anexos entram depois que o item for criado.
          </p>
        </div>
      )}

      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 18 }}>
        <button type="button" className="botao" onClick={aoCancelar} disabled={ocupado}>
          Cancelar
        </button>
        <button type="submit" className="botao botao-acao" disabled={ocupado}>
          {ocupado ? "Salvando…" : editando ? "Salvar" : "Criar item"}
        </button>
      </div>
    </form>
  );
}
