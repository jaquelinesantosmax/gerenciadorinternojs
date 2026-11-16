import Link from "next/link";
import type { ReactNode } from "react";
import type { DocTexto } from "@/lib/api";

// Mostra o texto formatado (descrição e comentários) montando os elementos um a um, sem HTML solto.
// Chaves de item no texto (ex.: LOP-12) viram link para o item.

interface No {
  type: string;
  text?: string;
  attrs?: Record<string, unknown>;
  marks?: { type: string; attrs?: Record<string, unknown> }[];
  content?: No[];
}

const CHAVE_ITEM = /\b([A-Z]{2,10}-\d{1,9})\b/g;

export function textoComChaves(texto: string, prefixo: string): ReactNode[] {
  const partes: ReactNode[] = [];
  let ultimo = 0;
  for (const achado of texto.matchAll(CHAVE_ITEM)) {
    const inicio = achado.index ?? 0;
    if (inicio > ultimo) partes.push(texto.slice(ultimo, inicio));
    partes.push(
      <Link key={`${prefixo}-${inicio}`} href={`/itens/${achado[1]}`}>
        {achado[1]}
      </Link>,
    );
    ultimo = inicio + achado[0].length;
  }
  if (ultimo < texto.length) partes.push(texto.slice(ultimo));
  return partes;
}

function comMarcas(conteudo: ReactNode, marcas: No["marks"], chave: string): ReactNode {
  let resultado = conteudo;
  for (const marca of marcas ?? []) {
    if (marca.type === "bold") resultado = <strong>{resultado}</strong>;
    if (marca.type === "italic") resultado = <em>{resultado}</em>;
    if (marca.type === "strike") resultado = <s>{resultado}</s>;
    if (marca.type === "code") resultado = <code className="codigo-inline">{resultado}</code>;
    if (marca.type === "link") {
      const href = String(marca.attrs?.href ?? "");
      // O servidor só aceita http, https e mailto; a conferência aqui é uma segunda proteção.
      if (/^(https?:\/\/|mailto:)/i.test(href)) {
        resultado = (
          <a href={href} target="_blank" rel="noopener noreferrer nofollow">
            {resultado}
          </a>
        );
      }
    }
  }
  return <span key={chave}>{resultado}</span>;
}

function montar(no: No, chave: string, imagens: Record<string, string>): ReactNode {
  const filhos = () => (no.content ?? []).map((f, i) => montar(f, `${chave}.${i}`, imagens));
  switch (no.type) {
    case "doc":
      return <>{filhos()}</>;
    case "text": {
      const temCodigoOuLink = no.marks?.some((m) => m.type === "code" || m.type === "link");
      const conteudo = temCodigoOuLink ? no.text ?? "" : textoComChaves(no.text ?? "", chave);
      return comMarcas(conteudo, no.marks, chave);
    }
    case "paragraph":
      return <p key={chave}>{filhos()}</p>;
    case "heading": {
      const nivel = Number(no.attrs?.level ?? 2);
      return nivel === 1 ? <h3 key={chave}>{filhos()}</h3> : nivel === 2 ? <h4 key={chave}>{filhos()}</h4> : <h5 key={chave}>{filhos()}</h5>;
    }
    case "bulletList":
      return <ul key={chave}>{filhos()}</ul>;
    case "orderedList":
      return <ol key={chave}>{filhos()}</ol>;
    case "listItem":
      return <li key={chave}>{filhos()}</li>;
    case "blockquote":
      return <blockquote key={chave}>{filhos()}</blockquote>;
    case "codeBlock":
      return (
        <pre key={chave}>
          <code>{(no.content ?? []).map((f) => f.text ?? "").join("")}</code>
        </pre>
      );
    case "hardBreak":
      return <br key={chave} />;
    case "horizontalRule":
      return <hr key={chave} />;
    case "table":
      return (
        <table key={chave}>
          <tbody>{filhos()}</tbody>
        </table>
      );
    case "tableRow":
      return <tr key={chave}>{filhos()}</tr>;
    case "tableHeader":
      return <th key={chave}>{filhos()}</th>;
    case "tableCell":
      return <td key={chave}>{filhos()}</td>;
    case "mention":
      return (
        <span key={chave} className="mencao">
          @{String(no.attrs?.label ?? "")}
        </span>
      );
    case "image": {
      const link = imagens[String(no.attrs?.anexoId ?? "")];
      return link ? (
        <img key={chave} src={link} alt={String(no.attrs?.alt ?? "")} />
      ) : (
        <span key={chave} className="legenda">
          [imagem removida]
        </span>
      );
    }
    default:
      return null;
  }
}

export function TextoRico({ doc, imagens = {} }: { doc: DocTexto | null | undefined; imagens?: Record<string, string> }) {
  if (!doc) return null;
  return <div className="texto-rico">{montar(doc as No, "r", imagens)}</div>;
}
