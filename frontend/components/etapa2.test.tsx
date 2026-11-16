import { render, screen } from "@testing-library/react";
import { descreverMudanca } from "@/app/(logado)/itens/[chave]/Atividade";
import { tamanhoLegivel } from "@/app/(logado)/itens/[chave]/Anexos";
import type { Campo, DocTexto } from "@/lib/api";
import { sugerirSigla } from "@/lib/formato";
import { textoDoCampo } from "./CampoPersonalizado";
import { paraEditar, paraSalvar } from "./Editor";
import { TextoRico } from "./TextoRico";

const doc = (content: unknown[]): DocTexto => ({ type: "doc", content });

describe("TextoRico", () => {
  it("transforma chaves de item em link e mostra menções", () => {
    render(
      <TextoRico
        doc={doc([
          {
            type: "paragraph",
            content: [
              { type: "text", text: "Ver LOP-12 com " },
              { type: "mention", attrs: { id: "1", label: "Ana Lima" } },
            ],
          },
        ])}
      />,
    );
    expect(screen.getByRole("link", { name: "LOP-12" })).toHaveAttribute("href", "/itens/LOP-12");
    expect(screen.getByText("@Ana Lima")).toBeInTheDocument();
  });

  it("ignora links perigosos e abre os seguros em nova aba", () => {
    render(
      <TextoRico
        doc={doc([
          {
            type: "paragraph",
            content: [
              { type: "text", text: "ruim", marks: [{ type: "link", attrs: { href: "javascript:alert(1)" } }] },
              { type: "text", text: " bom", marks: [{ type: "link", attrs: { href: "https://jusbrasil.com.br" } }] },
            ],
          },
        ])}
      />,
    );
    expect(screen.queryByRole("link", { name: "ruim" })).toBeNull();
    const bom = screen.getByRole("link", { name: "bom" });
    expect(bom).toHaveAttribute("target", "_blank");
    expect(bom).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });

  it("mostra imagens pelo link temporário do anexo", () => {
    render(<TextoRico doc={doc([{ type: "image", attrs: { anexoId: "a1", alt: "print" } }])} imagens={{ a1: "/api/anexos/a1/conteudo?x" }} />);
    expect(screen.getByRole("img", { name: "print" })).toHaveAttribute("src", "/api/anexos/a1/conteudo?x");
  });
});

describe("Editor: imagens", () => {
  it("guarda só o id do anexo e põe o link ao editar", () => {
    const comLink = doc([{ type: "image", attrs: { anexoId: "a1", alt: "x", src: "/tmp", title: null } }]);
    expect(paraSalvar(comLink)).toEqual(doc([{ type: "image", attrs: { anexoId: "a1", alt: "x" } }]));
    expect(paraEditar(doc([{ type: "image", attrs: { anexoId: "a1" } }]), { a1: "/link" })).toEqual(
      doc([{ type: "image", attrs: { anexoId: "a1", src: "/link" } }]),
    );
  });
});

describe("campos personalizados", () => {
  const base = { id: "c", nome: "C", obrigatorio: false, tipos_item: [], ativo: true };
  it("mostra cada tipo de valor de forma legível", () => {
    const lista: Campo = { ...base, tipo: "lista_cascata", config: { opcoes: [{ id: "p", nome: "Cível", filhos: [{ id: "f", nome: "Família" }] }] } };
    expect(textoDoCampo(lista, { pai: "p", filho: "f" }, [])).toBe("Cível › Família");
    const moeda: Campo = { ...base, tipo: "moeda", config: { moeda: "BRL" } };
    expect(textoDoCampo(moeda, "1500.50", [])?.replace(/\s/g, " ")).toBe("R$ 1.500,50");
    const pessoa: Campo = { ...base, tipo: "pessoa", config: { varias: true } };
    expect(textoDoCampo(pessoa, ["1", "2"], [{ id: "1", nome: "Ana", email: "", foto_url: null }, { id: "2", nome: "Bia", email: "", foto_url: null }])).toBe("Ana, Bia");
    expect(textoDoCampo({ ...base, tipo: "sim_nao", config: {} }, false, [])).toBe("Não");
    expect(textoDoCampo({ ...base, tipo: "data", config: {} }, "2026-12-01", [])).toBe("01/12/2026");
    expect(textoDoCampo({ ...base, tipo: "texto_curto", config: {} }, null, [])).toBeNull();
  });
});

describe("textos auxiliares", () => {
  it("sugere sigla pelo nome", () => {
    expect(sugerirSigla("Legal Ops")).toBe("LO");
    expect(sugerirSigla("Suporte B2B")).toBe("SUP");
    expect(sugerirSigla("Suporte TI")).toBe("ST");
    expect(sugerirSigla("Operações de Prazos Jurídicos")).toBe("OPJ");
    expect(sugerirSigla("Financeiro")).toBe("FIN");
  });

  it("descreve mudanças do histórico", () => {
    const h = { tipo: "historico" as const, id: "1", quando: "", autor: null };
    expect(descreverMudanca({ ...h, campo: "Status", valor_anterior: "A fazer", valor_novo: "Em andamento" })).toBe("mudou Status: A fazer → Em andamento");
    expect(descreverMudanca({ ...h, campo: "Categorias", valor_anterior: null, valor_novo: "x" })).toBe("preencheu Categorias: x");
    expect(descreverMudanca({ ...h, campo: "Anexos", valor_anterior: "a.pdf", valor_novo: null })).toBe("excluiu o anexo a.pdf");
  });

  it("mostra tamanhos de arquivo", () => {
    expect(tamanhoLegivel(500)).toBe("500 B");
    expect(tamanhoLegivel(340 * 1024)).toBe("340 KB");
    expect(tamanhoLegivel(1.2 * 1024 * 1024)).toBe("1,2 MB");
  });
});
