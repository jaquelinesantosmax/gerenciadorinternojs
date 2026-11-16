"use client";

import { useEffect, useState } from "react";
import { api, type Pessoa } from "@/lib/api";

/** Campo para achar uma pessoa pelo nome ou e-mail (ela precisa ter entrado no sistema uma vez). */
export function BuscaPessoa({
  rotulo,
  jaEscolhidas,
  textoJaEscolhida,
  aoEscolher,
}: {
  rotulo: string;
  jaEscolhidas: Set<string>;
  textoJaEscolhida: string;
  aoEscolher: (p: Pessoa) => void | Promise<void>;
}) {
  const [busca, setBusca] = useState("");
  const [achadas, setAchadas] = useState<Pessoa[]>([]);
  const id = `busca-${rotulo.replace(/\W+/g, "-").toLowerCase()}`;

  useEffect(() => {
    if (busca.trim().length < 2) {
      setAchadas([]);
      return;
    }
    const espera = setTimeout(() => api.pessoas(busca.trim()).then(setAchadas).catch(() => setAchadas([])), 250);
    return () => clearTimeout(espera);
  }, [busca]);

  return (
    <div style={{ position: "relative", flex: 1, minWidth: 220 }}>
      <label className="rotulo" htmlFor={id}>
        {rotulo}
      </label>
      <input id={id} className="campo" placeholder="Nome ou e-mail (a pessoa precisa ter entrado uma vez)" value={busca} onChange={(e) => setBusca(e.target.value)} />
      {achadas.length > 0 && (
        <ul className="sugestoes-busca">
          {achadas.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                disabled={jaEscolhidas.has(p.id)}
                onClick={async () => {
                  await aoEscolher(p);
                  setBusca("");
                }}
              >
                {p.nome} <span className="legenda">{p.email}</span>
                {jaEscolhidas.has(p.id) && <span className="legenda"> · {textoJaEscolhida}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
      <style>{`
        .sugestoes-busca{position:absolute;left:0;right:0;top:100%;margin:4px 0 0;padding:4px;list-style:none;background:#fff;border:0.5px solid var(--borda);border-radius:8px;z-index:10}
        .sugestoes-busca button{width:100%;text-align:left;border:none;background:none;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:13px}
        .sugestoes-busca button:hover:not(:disabled){background:var(--verde-fundo)}
        .sugestoes-busca button:disabled{opacity:.6;cursor:default}
      `}</style>
    </div>
  );
}
