"use client";

import { IconInfoCircle } from "@tabler/icons-react";
import { useEu } from "@/components/Moldura";
import { primeiroNome } from "@/lib/formato";

export default function Inicio() {
  const { eu } = useEu();
  return (
    <>
      <h1 className="h1">Olá, {primeiroNome(eu.nome)}</h1>
      {/* Decisão de 16/11. Os espaços chegam na Etapa 2; por enquanto ninguém tem espaço. */}
      <div className="painel" style={{ marginTop: 20, display: "flex", gap: 12, alignItems: "flex-start", maxWidth: 620 }}>
        <IconInfoCircle size={20} stroke={1.5} color="var(--verde)" style={{ flexShrink: 0, marginTop: 1 }} />
        <div>
          <div style={{ fontWeight: 500 }}>Você ainda não tem acesso a nenhum espaço.</div>
          <div style={{ marginTop: 2, color: "var(--texto-2)" }}>Peça acesso ao ADM do espaço em que vai trabalhar.</div>
        </div>
      </div>
    </>
  );
}
