import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Card } from "@/lib/api";
import { formatarValor, valorDoCard } from "./PlanejamentoScrum";
import { Burndown, escalaY, FluxoAcumulado, TempoCiclo, Velocidade } from "./Relatorios";

describe("estimativa no Scrum", () => {
  const card = { estimativa: "5.00", estimativa_horas: "12.50" } as Card;
  it("usa a unidade do quadro", () => {
    expect(valorDoCard(card, "pontos")).toBe(5);
    expect(valorDoCard(card, "horas")).toBe(12.5);
    expect(valorDoCard(card, "itens")).toBe(1);
    expect(valorDoCard({} as Card, "pontos")).toBe(0);
  });
  it("escreve o valor com a unidade", () => {
    expect(formatarValor("8.00", "pontos")).toBe("8 pts");
    expect(formatarValor(12.5, "horas")).toBe("12,5 h");
    expect(formatarValor(1, "itens")).toBe("1 item");
    expect(formatarValor(3, "itens")).toBe("3 itens");
  });
});

describe("gráficos", () => {
  it("contagem de itens usa só marcas inteiras no eixo", () => {
    expect(escalaY(1, true).marcas).toEqual([0, 1, 2, 3, 4]);
    expect(escalaY(7, true).marcas).toEqual([0, 2, 4, 6, 8]);
  });

  it("burndown tem legenda, rótulo do último ponto e dica ao passar o mouse", async () => {
    const pontos = [
      { dia: "2026-11-16", restante: "10", ideal: "10", escopo: "10" },
      { dia: "2026-11-17", restante: "6", ideal: "5", escopo: "10" },
      { dia: "2026-11-18", restante: null, ideal: "0", escopo: null },
    ];
    const { container } = render(<Burndown pontos={pontos} unidade="pontos" />);
    expect(screen.getByText("Restante")).toBeInTheDocument();
    expect(screen.getByText("Ideal")).toBeInTheDocument();
    expect(screen.getByText("6 pts")).toBeInTheDocument();
    await userEvent.hover(container.querySelectorAll("rect")[1]);
    expect(screen.getByRole("status")).toHaveTextContent("Restante: 6 pts");
  });

  it("burndown sem sprint iniciada explica", () => {
    render(<Burndown pontos={[]} unidade="pontos" />);
    expect(screen.getByText("O burndown aparece quando a sprint começa.")).toBeInTheDocument();
  });

  it("velocidade compara compromisso e entregue", async () => {
    const { container } = render(<Velocidade linhas={[{ sprint: "Sprint 1", compromisso: "8", entregue: "5" }]} unidade="pontos" />);
    expect(screen.getByText("Compromisso no início")).toBeInTheDocument();
    // Primeiro grupo é o dos eixos; o segundo é o da sprint.
    await userEvent.hover(container.querySelectorAll("svg[role=img] > g")[1].querySelector("rect") as Element);
    expect(screen.getByRole("status")).toHaveTextContent("Entregue: 5 pts");
  });

  it("fluxo acumulado mostra as três categorias", () => {
    render(<FluxoAcumulado dias={[{ dia: "2026-11-16", a_fazer: 2, em_andamento: 1, concluido: 0 }, { dia: "2026-11-17", a_fazer: 1, em_andamento: 1, concluido: 1 }]} />);
    ["A fazer", "Em andamento", "Concluído"].forEach((n) => expect(screen.getByText(n)).toBeInTheDocument());
  });

  it("tempo de ciclo mostra média, mediana e 85%", () => {
    render(<TempoCiclo dados={{ itens: [{ chave: "LOP-1", resumo: "X", inicio: "2026-11-10T12:00:00Z", fim: "2026-11-12T12:00:00Z", dias: 2 }], media: 2, mediana: 2, p85: 2 }} />);
    expect(screen.getByText("85% dos itens em até")).toBeInTheDocument();
    expect(screen.getAllByText("2 dias").length).toBe(3);
  });
});
