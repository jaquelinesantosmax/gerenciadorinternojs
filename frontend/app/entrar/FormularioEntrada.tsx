"use client";

import { useState } from "react";
import { api, ErroApi } from "@/lib/api";

/** Login de teste: só existe no desenvolvimento, até a credencial Google da empresa chegar. */
export function FormularioEntrada({ aoEntrar }: { aoEntrar: () => void }) {
  const [email, setEmail] = useState("");
  const [nome, setNome] = useState("");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    if (!email.trim()) {
      setErro("Informe o e-mail.");
      return;
    }
    setOcupado(true);
    try {
      await api.entrarTeste(email, nome);
      aoEntrar();
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível entrar.");
      setOcupado(false);
    }
  }

  return (
    <form onSubmit={enviar} noValidate>
      <span className="etiqueta etiqueta-teste">Login de teste · só no desenvolvimento</span>
      <div style={{ marginTop: 16 }}>
        <label className="rotulo" htmlFor="email">
          E-mail da empresa
        </label>
        <input
          id="email"
          className="campo"
          type="email"
          autoComplete="email"
          placeholder="nome@jusbrasil.com.br"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
      </div>
      <div style={{ marginTop: 12 }}>
        <label className="rotulo" htmlFor="nome">
          Nome <span className="legenda">(usado só no primeiro acesso)</span>
        </label>
        <input
          id="nome"
          className="campo"
          autoComplete="name"
          value={nome}
          onChange={(e) => setNome(e.target.value)}
        />
      </div>
      {erro && (
        <p className="mensagem-erro" role="alert" style={{ margin: "10px 0 0" }}>
          {erro}
        </p>
      )}
      <button className="botao botao-acao" type="submit" disabled={ocupado} style={{ marginTop: 18, width: "100%", justifyContent: "center", padding: "9px 12px" }}>
        {ocupado ? "Entrando…" : "Entrar"}
      </button>
      <p className="legenda" style={{ marginTop: 12 }}>
        Sem senha: qualquer e-mail @jusbrasil.com.br ou @digesto.com.br entra. Quando a credencial da empresa chegar, este
        formulário dá lugar ao botão Entrar com Google.
      </p>
    </form>
  );
}
