import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { FormularioEntrada } from "@/app/entrar/FormularioEntrada";
import { Dialogo } from "./Dialogo";
import { LinhaDoTempo } from "./LinhaDoTempo";

function respostaJson(status: number, corpo: unknown) {
  return Promise.resolve(new Response(JSON.stringify(corpo), { status, headers: { "Content-Type": "application/json" } }));
}

describe("FormularioEntrada", () => {
  it("envia e-mail e nome com o cabeçalho de proteção e avisa quando entrou", async () => {
    const fetchFalso = vi.spyOn(globalThis, "fetch").mockImplementation(() => respostaJson(200, { id: "1" }));
    const aoEntrar = vi.fn();
    render(<FormularioEntrada aoEntrar={aoEntrar} />);

    await userEvent.type(screen.getByLabelText("E-mail da empresa"), "ana@jusbrasil.com.br");
    await userEvent.type(screen.getByLabelText(/Nome/), "Ana Lima");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(aoEntrar).toHaveBeenCalled();
    const [url, opcoes] = fetchFalso.mock.calls[0];
    expect(url).toBe("/api/auth/teste/entrar");
    expect(opcoes?.method).toBe("POST");
    expect((opcoes?.headers as Record<string, string>)["X-Gerenciador"]).toBe("1");
    expect(JSON.parse(String(opcoes?.body))).toEqual({ email: "ana@jusbrasil.com.br", nome: "Ana Lima" });
  });

  it("mostra a mensagem do servidor quando a entrada é recusada", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() =>
      respostaJson(403, { detail: "Use sua conta da Jusbrasil ou da Digesto para entrar." }),
    );
    const aoEntrar = vi.fn();
    render(<FormularioEntrada aoEntrar={aoEntrar} />);

    await userEvent.type(screen.getByLabelText("E-mail da empresa"), "x@gmail.com");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Use sua conta da Jusbrasil ou da Digesto para entrar.");
    expect(aoEntrar).not.toHaveBeenCalled();
  });

  it("pede o e-mail antes de enviar", async () => {
    const fetchFalso = vi.spyOn(globalThis, "fetch");
    render(<FormularioEntrada aoEntrar={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Informe o e-mail.");
    expect(fetchFalso).not.toHaveBeenCalled();
  });

  it("avisa quando o servidor está desligado", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));
    render(<FormularioEntrada aoEntrar={vi.fn()} />);
    await userEvent.type(screen.getByLabelText("E-mail da empresa"), "a@jusbrasil.com.br");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Sem conexão com o servidor");
  });
});

describe("Dialogo", () => {
  it("confirma, cancela e fecha com Esc", async () => {
    const aoConfirmar = vi.fn();
    const aoCancelar = vi.fn();
    render(
      <Dialogo aberto titulo="Desativar Bruno?" textoConfirmar="Desativar" perigo aoConfirmar={aoConfirmar} aoCancelar={aoCancelar}>
        Texto
      </Dialogo>,
    );
    expect(screen.getByRole("dialog")).toHaveAccessibleName("Desativar Bruno?");
    // O foco começa em Cancelar, para ninguém confirmar uma ação séria sem querer.
    expect(screen.getByRole("button", { name: "Cancelar" })).toHaveFocus();
    await userEvent.click(screen.getByRole("button", { name: "Desativar" }));
    expect(aoConfirmar).toHaveBeenCalledTimes(1);
    await userEvent.keyboard("{Escape}");
    expect(aoCancelar).toHaveBeenCalledTimes(1);
  });

  it("não aparece fechado e mostra erro quando houver", () => {
    const { rerender } = render(
      <Dialogo aberto={false} titulo="X" textoConfirmar="Ok" aoConfirmar={vi.fn()} aoCancelar={vi.fn()}>
        Texto
      </Dialogo>,
    );
    expect(screen.queryByRole("dialog")).toBeNull();
    rerender(
      <Dialogo aberto titulo="X" textoConfirmar="Ok" erro="Falhou" aoConfirmar={vi.fn()} aoCancelar={vi.fn()}>
        Texto
      </Dialogo>,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Falhou");
  });
});

describe("LinhaDoTempo", () => {
  it("mostra a frase e o horário de cada evento", () => {
    render(
      <LinhaDoTempo
        eventos={[
          { id: 2, ocorrido_em: "2026-11-16T13:05:00Z", tipo: "logout", ator: { id: "1", nome: "Ana", email: "a@x", foto_url: null }, alvo: null, detalhes: {}, ip: "10.0.0.1" },
        ]}
        mostrarIp
      />,
    );
    expect(screen.getByText("Ana saiu")).toBeInTheDocument();
    expect(screen.getByText("16/11/2026, 10:05")).toBeInTheDocument();
    expect(screen.getByText(/IP 10.0.0.1/)).toBeInTheDocument();
  });

  it("avisa quando não há eventos", () => {
    render(<LinhaDoTempo eventos={[]} />);
    expect(screen.getByText("Nenhum evento registrado.")).toBeInTheDocument();
  });
});
