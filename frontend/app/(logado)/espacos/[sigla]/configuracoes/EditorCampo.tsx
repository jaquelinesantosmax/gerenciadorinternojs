"use client";

import { IconPlus, IconX } from "@tabler/icons-react";
import { useState } from "react";
import { api, ErroApi, type Campo, type OpcaoCampo, type TipoCampo, type TipoRef } from "@/lib/api";

const NOMES_TIPO: Record<TipoCampo, string> = {
  texto_curto: "Texto curto",
  texto_longo: "Texto longo",
  numero: "Número",
  moeda: "Moeda",
  data: "Data",
  data_hora: "Data e hora",
  url: "URL",
  lista_unica: "Lista de escolha única",
  lista_multipla: "Lista de escolha múltipla",
  lista_cascata: "Lista em cascata",
  pessoa: "Pessoa",
  sim_nao: "Sim/Não",
};
export { NOMES_TIPO };

const LISTAS: TipoCampo[] = ["lista_unica", "lista_multipla", "lista_cascata"];

function EditorOpcoes({ opcoes, aoMudar, nivel = 0 }: { opcoes: OpcaoCampo[]; aoMudar: (o: OpcaoCampo[]) => void; nivel?: number }) {
  const visiveis = opcoes.filter((o) => o.ativo !== false);
  return (
    <div style={{ display: "grid", gap: 6, marginLeft: nivel ? 22 : 0 }}>
      {visiveis.map((o) => {
        const indice = opcoes.indexOf(o);
        const atualizar = (nova: OpcaoCampo) => aoMudar(opcoes.map((x, i) => (i === indice ? nova : x)));
        return (
          <div key={o.id ?? `nova-${indice}`}>
            <div style={{ display: "flex", gap: 6 }}>
              <input className="campo" aria-label={nivel ? "Opção do segundo nível" : "Opção"} value={o.nome} onChange={(e) => atualizar({ ...o, nome: e.target.value })} />
              <button
                type="button"
                className="botao botao-discreto"
                aria-label={`Tirar a opção ${o.nome}`}
                // Opção que já existe vira inativa (continua nos itens que a usam); opção nova some.
                onClick={() => aoMudar(o.id ? opcoes.map((x, i) => (i === indice ? { ...x, ativo: false } : x)) : opcoes.filter((_, i) => i !== indice))}
              >
                <IconX size={14} stroke={1.5} />
              </button>
            </div>
            {nivel === 0 && o.filhos !== undefined && (
              <div style={{ marginTop: 6 }}>
                <EditorOpcoes opcoes={o.filhos} aoMudar={(filhos) => atualizar({ ...o, filhos })} nivel={1} />
              </div>
            )}
          </div>
        );
      })}
      <button type="button" className="botao botao-discreto" style={{ justifySelf: "start" }} onClick={() => aoMudar([...opcoes, { nome: "", ...(nivel === 0 && opcoes.some((o) => o.filhos) ? { filhos: [] } : {}) }])}>
        <IconPlus size={14} stroke={1.5} /> {nivel ? "Opção do segundo nível" : "Opção"}
      </button>
    </div>
  );
}

/** Criar ou editar um campo personalizado. O tipo não muda depois de criado. */
export function EditorCampo({
  sigla,
  tipos,
  moedas,
  campo,
  aoSalvar,
  aoCancelar,
}: {
  sigla: string;
  tipos: TipoRef[];
  moedas: Record<string, string>;
  campo: Campo | null;
  aoSalvar: () => Promise<void>;
  aoCancelar: () => void;
}) {
  const [nome, setNome] = useState(campo?.nome ?? "");
  const [tipo, setTipo] = useState<TipoCampo>(campo?.tipo ?? "texto_curto");
  const [obrigatorio, setObrigatorio] = useState(campo?.obrigatorio ?? false);
  const [tiposItem, setTiposItem] = useState<string[]>(campo?.tipos_item ?? tipos.filter((t) => t.nivel !== "epico").map((t) => t.id));
  const [opcoes, setOpcoes] = useState<OpcaoCampo[]>(campo?.config.opcoes ?? []);
  const [moeda, setMoeda] = useState(campo?.config.moeda ?? "BRL");
  const [varias, setVarias] = useState(campo?.config.varias ?? false);
  const [textoCaixa, setTextoCaixa] = useState(campo?.config.texto ?? "");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const ehLista = LISTAS.includes(tipo);
  const config = ehLista
    ? { opcoes: opcoes.filter((o) => o.nome.trim() || o.id).map((o) => ({ ...o, filhos: o.filhos?.filter((f) => f.nome.trim() || f.id) })) }
    : tipo === "moeda"
      ? { moeda }
      : tipo === "pessoa"
        ? { varias }
        : tipo === "sim_nao"
          ? { texto: textoCaixa }
          : {};

  async function salvar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setOcupado(true);
    try {
      if (campo) await api.editarCampo(sigla, campo.id, { nome, obrigatorio, tipos_item: tiposItem, config });
      else await api.criarCampo(sigla, { nome, tipo, obrigatorio, tipos_item: tiposItem, config });
      await aoSalvar();
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível salvar.");
      setOcupado(false);
    }
  }

  return (
    <form onSubmit={salvar} noValidate>
      <div className="grade-campos">
        <div>
          <label className="rotulo obrigatorio" htmlFor="campo-nome">
            Nome
          </label>
          <input id="campo-nome" className="campo" maxLength={80} value={nome} onChange={(e) => setNome(e.target.value)} autoFocus />
        </div>
        <div>
          <label className="rotulo obrigatorio" htmlFor="campo-tipo">
            Tipo de campo
          </label>
          <select
            id="campo-tipo"
            className="campo"
            value={tipo}
            disabled={Boolean(campo)}
            onChange={(e) => {
              const novo = e.target.value as TipoCampo;
              setTipo(novo);
              if (LISTAS.includes(novo) && opcoes.length === 0) setOpcoes([{ nome: "", ...(novo === "lista_cascata" ? { filhos: [] } : {}) }]);
              if (novo === "lista_cascata") setOpcoes((o) => o.map((x) => ({ ...x, filhos: x.filhos ?? [] })));
            }}
          >
            {Object.entries(NOMES_TIPO).map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
          {campo && <span className="legenda">O tipo não muda depois de criado.</span>}
        </div>
        {tipo === "moeda" && (
          <div>
            <label className="rotulo obrigatorio" htmlFor="campo-moeda">
              Moeda
            </label>
            <select id="campo-moeda" className="campo" value={moeda} onChange={(e) => setMoeda(e.target.value)}>
              {Object.entries(moedas).map(([codigo, rotulo]) => (
                <option key={codigo} value={codigo}>
                  {rotulo} ({codigo})
                </option>
              ))}
            </select>
          </div>
        )}
        {tipo === "sim_nao" && (
          <div style={{ gridColumn: "1 / -1" }}>
            <label className="rotulo" htmlFor="campo-texto">
              Texto ao lado da caixa
            </label>
            <input id="campo-texto" className="campo" maxLength={200} placeholder="Ex.: Envolve outra área?" value={textoCaixa} onChange={(e) => setTextoCaixa(e.target.value)} />
            <span className="legenda" style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 6 }}>
              Prévia: <input type="checkbox" disabled aria-hidden="true" /> {textoCaixa || "Sim"}
            </span>
          </div>
        )}
        {tipo === "pessoa" && (
          <label style={{ display: "flex", gap: 6, alignItems: "center", alignSelf: "end", height: 36 }}>
            <input type="checkbox" checked={varias} onChange={(e) => setVarias(e.target.checked)} />
            Permite escolher várias pessoas
          </label>
        )}
      </div>
      {ehLista && (
        <div style={{ marginTop: 14 }}>
          <span className="rotulo obrigatorio">Opções{tipo === "lista_cascata" ? " (com segundo nível)" : ""}</span>
          <EditorOpcoes opcoes={opcoes} aoMudar={setOpcoes} />
          {campo && <p className="legenda">Opções retiradas continuam nos itens que já as usam, mas saem da lista de escolha.</p>}
        </div>
      )}
      <fieldset style={{ border: "none", padding: 0, margin: "14px 0 0" }}>
        <legend className="rotulo obrigatorio">Aparece nos tipos</legend>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 14px" }}>
          {tipos.map((t) => (
            <label key={t.id} style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
              <input type="checkbox" checked={tiposItem.includes(t.id)} onChange={(e) => setTiposItem(e.target.checked ? [...tiposItem, t.id] : tiposItem.filter((x) => x !== t.id))} />
              {t.nome}
            </label>
          ))}
        </div>
      </fieldset>
      <label style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 12 }}>
        <input type="checkbox" checked={obrigatorio} onChange={(e) => setObrigatorio(e.target.checked)} />
        Obrigatório
      </label>
      {obrigatorio && campo && !campo.obrigatorio && (
        <p className="legenda" style={{ margin: "4px 0 0" }}>
          Vale para itens novos. Itens que já existem só são cobrados quando alguém mexer neste campo.
        </p>
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
          {campo ? "Salvar campo" : "Criar campo"}
        </button>
      </div>
    </form>
  );
}
