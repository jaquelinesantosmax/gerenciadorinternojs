"use client";

import { useEffect, useRef } from "react";

/** Janela de confirmação para ações que mudam acessos (desativar, retirar papel, remover domínio). */
export function Dialogo({
  aberto,
  titulo,
  children,
  textoConfirmar,
  perigo = false,
  ocupado = false,
  erro,
  aoConfirmar,
  aoCancelar,
}: {
  aberto: boolean;
  titulo: string;
  children: React.ReactNode;
  textoConfirmar: string;
  perigo?: boolean;
  ocupado?: boolean;
  erro?: string | null;
  aoConfirmar: () => void;
  aoCancelar: () => void;
}) {
  const cancelar = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!aberto) return;
    cancelar.current?.focus();
    const tecla = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !ocupado) aoCancelar();
    };
    document.addEventListener("keydown", tecla);
    return () => document.removeEventListener("keydown", tecla);
  }, [aberto, ocupado, aoCancelar]);

  if (!aberto) return null;

  return (
    <div className="fundo-dialogo" onMouseDown={(e) => e.target === e.currentTarget && !ocupado && aoCancelar()}>
      <div className="dialogo" role="dialog" aria-modal="true" aria-labelledby="titulo-dialogo">
        <h2 id="titulo-dialogo" className="h2" style={{ color: perigo ? "var(--alerta)" : undefined }}>
          {titulo}
        </h2>
        <div style={{ marginTop: 8, lineHeight: 1.6 }}>{children}</div>
        {erro && (
          <p className="mensagem-erro" role="alert" style={{ marginBottom: 0 }}>
            {erro}
          </p>
        )}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 18 }}>
          <button ref={cancelar} className="botao" onClick={aoCancelar} disabled={ocupado}>
            Cancelar
          </button>
          <button
            className={`botao ${perigo ? "botao-perigo-cheio" : "botao-acao"}`}
            onClick={aoConfirmar}
            disabled={ocupado}
          >
            {ocupado ? "Aguarde…" : textoConfirmar}
          </button>
        </div>
      </div>
      <style>{`
        .fundo-dialogo{position:fixed;inset:0;background:rgba(16,23,41,.45);display:flex;align-items:center;justify-content:center;padding:16px;z-index:50}
        .dialogo{background:#fff;border-radius:12px;padding:20px 22px;width:100%;max-width:440px;border:0.5px solid var(--borda)}
      `}</style>
    </div>
  );
}
