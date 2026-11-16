"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api, type Provedores } from "@/lib/api";
import { FormularioEntrada } from "./FormularioEntrada";

export default function PaginaEntrar() {
  const router = useRouter();
  const [provedores, setProvedores] = useState<Provedores | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    // Quem já tem sessão vai direto para o início.
    api
      .eu()
      .then(() => router.replace("/"))
      .catch(() => api.provedores().then(setProvedores).catch((e: Error) => setErro(e.message)));
  }, [router]);

  return (
    <main className="entrada">
      <section className="entrada-faixa">
        <div style={{ fontSize: 28, fontWeight: 600, letterSpacing: "-0.5px" }}>Gerenciador</div>
        <div style={{ fontSize: 13, fontWeight: 300, color: "var(--verde-claro)", marginTop: 4 }}>
          Projetos, tarefas e service desk
          <br />
          Jusbrasil e Digesto
        </div>
      </section>
      <section className="entrada-ficha">
        <h1 className="h1">Entrar</h1>
        <p className="legenda" style={{ marginTop: 4 }}>
          Use sua conta da Jusbrasil ou da Digesto.
        </p>
        <div style={{ marginTop: 20 }}>
          {erro && (
            <p className="mensagem-erro" role="alert">
              {erro}
            </p>
          )}
          {provedores?.teste && <FormularioEntrada aoEntrar={() => router.replace("/")} />}
          {provedores && !provedores.teste && !provedores.google && (
            <p className="caixa-alerta">Nenhuma forma de entrada está configurada. Fale com o ADM da plataforma.</p>
          )}
        </div>
      </section>
      <style>{`
        .entrada{min-height:100vh;display:grid;grid-template-columns:minmax(220px,320px) minmax(0,460px);align-content:center;justify-content:center;padding:24px}
        .entrada-faixa{background:var(--verde-escuro);color:#fff;padding:28px 24px;border-radius:12px 0 0 12px;display:flex;flex-direction:column;justify-content:flex-end;min-height:420px}
        .entrada-ficha{background:#fff;border:0.5px solid var(--borda);border-left:none;border-radius:0 12px 12px 0;padding:32px 30px}
        @media (max-width:700px){.entrada{grid-template-columns:1fr;padding:16px}.entrada-faixa{border-radius:12px 12px 0 0;min-height:auto}.entrada-ficha{border-left:0.5px solid var(--borda);border-top:none;border-radius:0 0 12px 12px}}
      `}</style>
    </main>
  );
}
