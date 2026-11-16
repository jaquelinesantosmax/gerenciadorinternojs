"use client";

import type { Campo, OpcaoCampo, Pessoa } from "@/lib/api";
import { formatarData, formatarDataHora } from "@/lib/formato";

// Entrada e exibição dos campos personalizados, um componente para cada tipo decidido em 16/11.

const ativas = (opcoes: OpcaoCampo[] | undefined, atual?: unknown) =>
  (opcoes ?? []).filter((o) => o.ativo !== false || o.id === atual);

/** Converte "2026-12-01T10:00" (horário de Brasília digitado) para ISO com fuso. */
function paraIsoBrasilia(local: string): string | null {
  if (!local) return null;
  return `${local}:00-03:00`;
}

function deIsoParaLocal(iso: unknown): string {
  if (typeof iso !== "string" || !iso) return "";
  const data = new Date(iso);
  const brasilia = new Date(data.getTime() - 3 * 3600 * 1000);
  return brasilia.toISOString().slice(0, 16);
}

export function EntradaCampo({
  campo,
  valor,
  aoMudar,
  membros,
  moedas,
}: {
  campo: Campo;
  valor: unknown;
  aoMudar: (v: unknown) => void;
  membros: Pessoa[];
  moedas: Record<string, string>;
}) {
  const id = `campo-${campo.id}`;
  const rotulo = (
    <label className={`rotulo${campo.obrigatorio ? " obrigatorio" : ""}`} htmlFor={id}>
      {campo.nome}
      {campo.tipo === "moeda" && campo.config.moeda ? ` (${moedas[campo.config.moeda] ?? campo.config.moeda})` : ""}
    </label>
  );
  const texto = (v: unknown) => (v === null || v === undefined ? "" : String(v));

  switch (campo.tipo) {
    case "texto_longo":
      return (
        <div style={{ gridColumn: "1 / -1" }}>
          {rotulo}
          <textarea id={id} className="campo" value={texto(valor)} onChange={(e) => aoMudar(e.target.value)} />
        </div>
      );
    case "sim_nao":
      return (
        <div>
          <span className="rotulo">{campo.nome}</span>
          <label style={{ display: "inline-flex", gap: 6, alignItems: "center", height: 36 }}>
            <input id={id} type="checkbox" checked={valor === true} onChange={(e) => aoMudar(e.target.checked)} />
            Sim
          </label>
        </div>
      );
    case "lista_unica":
      return (
        <div>
          {rotulo}
          <select id={id} className="campo" value={texto(valor)} onChange={(e) => aoMudar(e.target.value || null)}>
            <option value="">—</option>
            {ativas(campo.config.opcoes, valor).map((o) => (
              <option key={o.id} value={o.id}>
                {o.nome}
              </option>
            ))}
          </select>
        </div>
      );
    case "lista_multipla": {
      const marcados = Array.isArray(valor) ? (valor as string[]) : [];
      return (
        <fieldset style={{ border: "none", padding: 0, margin: 0 }}>
          <legend className={`rotulo${campo.obrigatorio ? " obrigatorio" : ""}`}>{campo.nome}</legend>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px" }}>
            {ativas(campo.config.opcoes, undefined)
              .concat((campo.config.opcoes ?? []).filter((o) => o.ativo === false && marcados.includes(o.id ?? "")))
              .map((o) => (
                <label key={o.id} style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={marcados.includes(o.id ?? "")}
                    onChange={(e) =>
                      aoMudar(e.target.checked ? [...marcados, o.id] : marcados.filter((m) => m !== o.id))
                    }
                  />
                  {o.nome}
                </label>
              ))}
          </div>
        </fieldset>
      );
    }
    case "lista_cascata": {
      const atual = (valor as { pai?: string; filho?: string | null } | null) ?? {};
      const pai = (campo.config.opcoes ?? []).find((o) => o.id === atual.pai);
      return (
        <div>
          {rotulo}
          <div style={{ display: "flex", gap: 6 }}>
            <select
              id={id}
              className="campo"
              value={atual.pai ?? ""}
              onChange={(e) => aoMudar(e.target.value ? { pai: e.target.value, filho: null } : null)}
            >
              <option value="">—</option>
              {ativas(campo.config.opcoes, atual.pai).map((o) => (
                <option key={o.id} value={o.id}>
                  {o.nome}
                </option>
              ))}
            </select>
            <select
              className="campo"
              aria-label={`${campo.nome}: segundo nível`}
              value={atual.filho ?? ""}
              disabled={!pai?.filhos?.length}
              onChange={(e) => aoMudar({ pai: atual.pai, filho: e.target.value || null })}
            >
              <option value="">—</option>
              {ativas(pai?.filhos, atual.filho).map((o) => (
                <option key={o.id} value={o.id}>
                  {o.nome}
                </option>
              ))}
            </select>
          </div>
        </div>
      );
    }
    case "pessoa": {
      if (campo.config.varias) {
        const marcados = Array.isArray(valor) ? (valor as string[]) : [];
        return (
          <fieldset style={{ border: "none", padding: 0, margin: 0 }}>
            <legend className={`rotulo${campo.obrigatorio ? " obrigatorio" : ""}`}>{campo.nome}</legend>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px" }}>
              {membros.map((p) => (
                <label key={p.id} style={{ display: "inline-flex", gap: 6, alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={marcados.includes(p.id)}
                    onChange={(e) => aoMudar(e.target.checked ? [...marcados, p.id] : marcados.filter((m) => m !== p.id))}
                  />
                  {p.nome}
                </label>
              ))}
            </div>
          </fieldset>
        );
      }
      return (
        <div>
          {rotulo}
          <select id={id} className="campo" value={texto(valor)} onChange={(e) => aoMudar(e.target.value || null)}>
            <option value="">—</option>
            {membros.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome}
              </option>
            ))}
          </select>
        </div>
      );
    }
    case "data_hora":
      return (
        <div>
          {rotulo}
          <input
            id={id}
            className="campo"
            type="datetime-local"
            value={deIsoParaLocal(valor)}
            onChange={(e) => aoMudar(paraIsoBrasilia(e.target.value))}
          />
        </div>
      );
    default: {
      const tipoHtml = { numero: "number", moeda: "number", data: "date", url: "url" }[campo.tipo as string] ?? "text";
      return (
        <div>
          {rotulo}
          <input
            id={id}
            className="campo"
            type={tipoHtml}
            step={campo.tipo === "moeda" ? "0.01" : "any"}
            placeholder={campo.tipo === "url" ? "https://" : undefined}
            value={texto(valor)}
            onChange={(e) => aoMudar(e.target.value)}
          />
        </div>
      );
    }
  }
}

/** Valor legível de um campo personalizado. */
export function textoDoCampo(campo: Campo, valor: unknown, pessoas: Pessoa[]): string | null {
  if (valor === null || valor === undefined || valor === "") return null;
  const opcoes = campo.config.opcoes ?? [];
  const nomeOpcao = (lista: OpcaoCampo[] | undefined, id: unknown) => lista?.find((o) => o.id === id)?.nome ?? "?";
  switch (campo.tipo) {
    case "lista_unica":
      return nomeOpcao(opcoes, valor);
    case "lista_multipla":
      return (valor as string[]).map((v) => nomeOpcao(opcoes, v)).join(", ");
    case "lista_cascata": {
      const v = valor as { pai: string; filho: string | null };
      const pai = opcoes.find((o) => o.id === v.pai);
      return pai ? pai.nome + (v.filho ? ` › ${nomeOpcao(pai.filhos, v.filho)}` : "") : "?";
    }
    case "pessoa": {
      const ids = Array.isArray(valor) ? (valor as string[]) : [valor as string];
      return ids.map((i) => pessoas.find((p) => p.id === i)?.nome ?? "?").join(", ");
    }
    case "sim_nao":
      return valor ? "Sim" : "Não";
    case "data":
      return formatarData(`${valor}T12:00:00Z`);
    case "data_hora":
      return formatarDataHora(String(valor));
    case "moeda": {
      try {
        return new Intl.NumberFormat("pt-BR", { style: "currency", currency: campo.config.moeda ?? "BRL" }).format(Number(valor));
      } catch {
        return String(valor);
      }
    }
    case "numero":
      return new Intl.NumberFormat("pt-BR").format(Number(valor));
    default:
      return String(valor);
  }
}
