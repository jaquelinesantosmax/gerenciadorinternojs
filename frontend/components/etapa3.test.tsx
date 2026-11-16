import type { BarraGantt, Card } from "@/lib/api";
import { ordenarHierarquia } from "./Gantt";
import { statusPossiveis } from "./QuadroKanban";

const st = (id: string, nome: string) => ({ id, nome, categoria: "em_andamento" as const, proprio: false, itens: 0 });

describe("quadro: arrastar card", () => {
  const card = { status_id: "afazer", status: "A fazer" } as Card;
  const destinos = { afazer: ["andamento", "cancelado"] };

  it("oferece só os status da coluna que o fluxo permite", () => {
    expect(statusPossiveis(card, { status: [st("andamento", "Em andamento")] }, destinos).map((s) => s.nome)).toEqual(["Em andamento"]);
    expect(statusPossiveis(card, { status: [st("concluido", "Concluído")] }, destinos)).toEqual([]);
  });

  it("numa coluna que junta vários status, lista os permitidos para a pessoa escolher", () => {
    const coluna = { status: [st("andamento", "Em andamento"), st("cancelado", "Cancelado"), st("concluido", "Concluído")] };
    expect(statusPossiveis(card, coluna, destinos).map((s) => s.id)).toEqual(["andamento", "cancelado"]);
  });
});

describe("Gantt", () => {
  const barra = (chave: string, pai: string | null = null) => ({ chave, pai }) as BarraGantt;

  it("põe cada filho logo abaixo do pai, com recuo", () => {
    const ordem = ordenarHierarquia([barra("A"), barra("B"), barra("A2", "A"), barra("A2a", "A2"), barra("C", "FORA")]);
    expect(ordem.map((b) => `${b.chave}:${b.nivelVisual}`)).toEqual(["A:0", "A2:1", "A2a:2", "B:0", "C:0"]);
  });
});
