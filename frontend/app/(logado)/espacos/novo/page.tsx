"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useEu } from "@/components/Moldura";
import { api, ErroApi } from "@/lib/api";
import { sugerirSigla } from "@/lib/formato";
import { DESCRICAO_MODELO, MODELOS } from "@/lib/textos";

export default function NovoEspaco() {
  const { eu } = useEu();
  const router = useRouter();
  const podeEquipe = eu.permissoes.criar_espaco_equipe;
  const [tipo, setTipo] = useState<"projeto" | "pessoal">(podeEquipe ? "projeto" : "pessoal");
  const [nome, setNome] = useState("");
  const [sigla, setSigla] = useState("");
  const [siglaTocada, setSiglaTocada] = useState(false);
  const [modelo, setModelo] = useState("kanban");
  const [erro, setErro] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  async function criar(e: React.FormEvent) {
    e.preventDefault();
    setErro(null);
    setOcupado(true);
    try {
      const espaco = await api.criarEspaco({ tipo, nome, sigla, modelo: tipo === "projeto" ? modelo : null });
      window.dispatchEvent(new Event("espacos-mudaram"));
      router.push(`/espacos/${espaco.sigla}`);
    } catch (falha) {
      setErro(falha instanceof ErroApi ? falha.message : "Não foi possível criar.");
      setOcupado(false);
    }
  }

  return (
    <form onSubmit={criar} style={{ maxWidth: 640 }} noValidate>
      <h1 className="h1">Criar espaço</h1>
      <fieldset style={{ border: "none", padding: 0, margin: "18px 0 0" }}>
        <legend className="rotulo">Tipo</legend>
        <div style={{ display: "grid", gap: 8 }}>
          {podeEquipe && (
            <label className={`opcao${tipo === "projeto" ? " marcada" : ""}`}>
              <input type="radio" name="tipo" checked={tipo === "projeto"} onChange={() => setTipo("projeto")} />
              <span>
                <b style={{ fontWeight: 500 }}>Espaço de projeto</b>
                <span className="legenda" style={{ display: "block" }}>
                  Para uma equipe. Você vira ADM do espaço e adiciona as pessoas.
                </span>
              </span>
            </label>
          )}
          <label className={`opcao${tipo === "pessoal" ? " marcada" : ""}`}>
            <input type="radio" name="tipo" checked={tipo === "pessoal"} onChange={() => setTipo("pessoal")} />
            <span>
              <b style={{ fontWeight: 500 }}>Espaço pessoal</b>
              <span className="legenda" style={{ display: "block" }}>
                Só você vê. Fica fora do alcance de Gestores e do ADM da plataforma.
              </span>
            </span>
          </label>
        </div>
      </fieldset>
      <div className="grade-campos" style={{ marginTop: 16 }}>
        <div>
          <label className="rotulo obrigatorio" htmlFor="nome">
            Nome
          </label>
          <input
            id="nome"
            className="campo"
            maxLength={120}
            value={nome}
            onChange={(e) => {
              setNome(e.target.value);
              if (!siglaTocada) setSigla(sugerirSigla(e.target.value));
            }}
          />
        </div>
        <div>
          <label className="rotulo obrigatorio" htmlFor="sigla">
            Sigla
          </label>
          <input
            id="sigla"
            className="campo"
            maxLength={10}
            value={sigla}
            style={{ textTransform: "uppercase", letterSpacing: ".04em" }}
            onChange={(e) => {
              setSiglaTocada(true);
              setSigla(e.target.value.toUpperCase().replace(/[^A-Z]/g, ""));
            }}
          />
          <span className="legenda">
            2 a 10 letras. Vira a chave dos itens ({sigla || "SIGLA"}-1) e não muda depois.
          </span>
        </div>
      </div>
      {tipo === "projeto" && (
        <fieldset style={{ border: "none", padding: 0, margin: "16px 0 0" }}>
          <legend className="rotulo obrigatorio">Modelo</legend>
          <div style={{ display: "grid", gap: 8 }}>
            {Object.entries(MODELOS).map(([valor, rotulo]) => (
              <label key={valor} className={`opcao${modelo === valor ? " marcada" : ""}`}>
                <input type="radio" name="modelo" checked={modelo === valor} onChange={() => setModelo(valor)} />
                <span>
                  <b style={{ fontWeight: 500 }}>{rotulo}</b>
                  <span className="legenda" style={{ display: "block" }}>
                    {DESCRICAO_MODELO[valor]}
                  </span>
                </span>
              </label>
            ))}
          </div>
          <p className="legenda">O quadro e o fluxo de trabalho do modelo chegam na próxima etapa. Por enquanto, os itens aparecem em lista.</p>
        </fieldset>
      )}
      {erro && (
        <p className="mensagem-erro" role="alert">
          {erro}
        </p>
      )}
      <div style={{ display: "flex", gap: 8, marginTop: 18 }}>
        <button type="submit" className="botao botao-acao" disabled={ocupado}>
          {ocupado ? "Criando…" : "Criar espaço"}
        </button>
        <button type="button" className="botao" onClick={() => router.back()}>
          Cancelar
        </button>
      </div>
      <style>{`
        .opcao{display:flex;gap:10px;align-items:flex-start;border:0.5px solid var(--borda);border-radius:8px;padding:10px 12px;cursor:pointer;background:#fff}
        .opcao.marcada{border-color:var(--verde);background:var(--verde-fundo)}
        .opcao input{margin-top:3px}
      `}</style>
    </form>
  );
}
