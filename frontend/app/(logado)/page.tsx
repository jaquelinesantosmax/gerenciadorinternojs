"use client";

import { IconFolder, IconInfoCircle, IconPlus, IconUser } from "@tabler/icons-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useEu } from "@/components/Moldura";
import { api, type EspacoResumo } from "@/lib/api";
import { primeiroNome } from "@/lib/formato";
import { MODELOS, NOME_PAPEL_ESPACO } from "@/lib/textos";

export default function Inicio() {
  const { eu } = useEu();
  const [espacos, setEspacos] = useState<EspacoResumo[] | null>(null);

  useEffect(() => {
    api.espacos().then(setEspacos).catch(() => setEspacos([]));
  }, []);

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <h1 className="h1">Olá, {primeiroNome(eu.nome)}</h1>
        <Link href="/espacos/novo" className="botao botao-acao">
          <IconPlus size={16} stroke={1.5} /> {eu.permissoes.criar_espaco_equipe ? "Criar espaço" : "Criar espaço pessoal"}
        </Link>
      </div>
      {espacos === null ? (
        <p className="legenda">Carregando…</p>
      ) : espacos.length === 0 ? (
        // Decisão de 16/11.
        <div className="painel" style={{ marginTop: 20, display: "flex", gap: 12, alignItems: "flex-start", maxWidth: 620 }}>
          <IconInfoCircle size={20} stroke={1.5} color="var(--verde)" style={{ flexShrink: 0, marginTop: 1 }} />
          <div>
            <div style={{ fontWeight: 500 }}>Você ainda não tem acesso a nenhum espaço.</div>
            <div style={{ marginTop: 2, color: "var(--texto-2)" }}>Peça acesso ao ADM do espaço em que vai trabalhar.</div>
          </div>
        </div>
      ) : (
        <div className="grade-espacos">
          {espacos.map((e) => (
            <Link key={e.id} href={`/espacos/${e.sigla}`} className="cartao-espaco">
              <span className="sigla">{e.sigla}</span>
              <span style={{ fontWeight: 500, color: "var(--texto)" }}>{e.nome}</span>
              <span className="legenda" style={{ display: "flex", gap: 4, alignItems: "center" }}>
                {e.tipo === "pessoal" ? <IconUser size={13} stroke={1.5} /> : <IconFolder size={13} stroke={1.5} />}
                {e.tipo === "pessoal" ? "Pessoal" : MODELOS[e.modelo ?? ""]} · {NOME_PAPEL_ESPACO[e.meu_papel]}
              </span>
            </Link>
          ))}
        </div>
      )}
      <style>{`
        .grade-espacos{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;margin-top:20px}
        .cartao-espaco{display:flex;flex-direction:column;gap:4px;background:#fff;border:0.5px solid var(--borda);border-radius:8px;padding:14px;text-decoration:none}
        .cartao-espaco:hover{border-color:var(--verde)}
        .cartao-espaco .sigla{font-size:12px;font-weight:600;color:var(--verde);letter-spacing:.04em}
      `}</style>
    </>
  );
}
