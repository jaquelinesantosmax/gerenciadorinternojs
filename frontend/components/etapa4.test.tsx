import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PedidosDeAcesso } from "@/app/(logado)/espacos/[sigla]/configuracoes/ConfigAcesso";
import { api, type EspacoDetalhe, type Evento } from "@/lib/api";
import { descreverEvento, eventoDeAlerta } from "@/lib/textos";
import { AcessoNoTopo, DialogoSuporte } from "./AcessoEspaco";

const base = {
  id: "1",
  sigla: "LOP",
  nome: "Legal Ops",
  tipo: "projeto",
  modelo: "kanban",
  paineis: [],
  descricao: null,
  criado_em: "2026-11-16T10:00:00Z",
  permissoes: {},
  tipos: [],
  status: [],
  origens: [],
  aberto: false,
  acompanha: false,
  suporte_ate: null,
  pode_acompanhar: false,
  pedido_pendente: false,
} as unknown as EspacoDetalhe;

afterEach(() => vi.restoreAllMocks());

describe("acesso no topo do espaço", () => {
  it("Gestor vê Acompanhar e o botão chama o servidor", async () => {
    const chamada = vi.spyOn(api, "acompanhar").mockResolvedValue(undefined);
    const aoMudar = vi.fn();
    render(<AcessoNoTopo espaco={{ ...base, meu_papel: "gestor", pode_acompanhar: true }} parte="botoes" aoMudar={aoMudar} />);
    await userEvent.click(screen.getByRole("button", { name: "Acompanhar" }));
    expect(chamada).toHaveBeenCalledWith("LOP", true);
    await waitFor(() => expect(aoMudar).toHaveBeenCalled());
  });

  it("Leitor pode pedir para virar Membro; com pedido pendente, só aparece o aviso", () => {
    const { rerender } = render(<AcessoNoTopo espaco={{ ...base, meu_papel: "leitor" }} parte="botoes" aoMudar={() => undefined} />);
    expect(screen.getByRole("button", { name: "Solicitar acesso" })).toBeInTheDocument();
    rerender(<AcessoNoTopo espaco={{ ...base, meu_papel: "leitor", pedido_pendente: true }} parte="botoes" aoMudar={() => undefined} />);
    expect(screen.queryByRole("button", { name: "Solicitar acesso" })).not.toBeInTheDocument();
    expect(screen.getByText("Acesso solicitado")).toBeInTheDocument();
  });

  it("Membro não vê Solicitar acesso nem Acompanhar", () => {
    render(<AcessoNoTopo espaco={{ ...base, meu_papel: "membro" }} parte="botoes" aoMudar={() => undefined} />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("em suporte, mostra a faixa com o prazo e o botão Sair do suporte", () => {
    render(<AcessoNoTopo espaco={{ ...base, meu_papel: "suporte", suporte_ate: "2026-11-16T17:00:00Z" }} parte="faixas" aoMudar={() => undefined} />);
    expect(screen.getByRole("status")).toHaveTextContent("até 16/11/2026, 14:00");
    expect(screen.getByRole("button", { name: "Sair do suporte" })).toBeInTheDocument();
  });
});

describe("suporte do ADM da plataforma", () => {
  it("exige o motivo antes de entrar", async () => {
    const entrar = vi.spyOn(api, "entrarSuporte").mockResolvedValue(undefined);
    render(<DialogoSuporte sigla="LOP" nome="Legal Ops" aberto aoFechar={() => undefined} aoEntrar={() => undefined} />);
    await userEvent.click(screen.getByRole("button", { name: "Entrar para suporte" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Informe o motivo do suporte.");
    expect(entrar).not.toHaveBeenCalled();
    await userEvent.type(screen.getByLabelText("Motivo"), "Chamado 123");
    await userEvent.click(screen.getByRole("button", { name: "Entrar para suporte" }));
    expect(entrar).toHaveBeenCalledWith("LOP", "Chamado 123");
  });
});

describe("pedidos de acesso", () => {
  it("Aprovar só libera depois de escolher o papel (nada vem marcado)", async () => {
    vi.spyOn(api, "pedidosAcesso").mockResolvedValue([
      { id: "p1", pessoa: { id: "u1", nome: "Ana Lima", email: "ana@jusbrasil.com.br", foto_url: null }, item_chave: "LOP-3", mensagem: "Preciso ver", criado_em: "2026-11-16T12:00:00Z" },
    ]);
    const aprovar = vi.spyOn(api, "aprovarPedido").mockResolvedValue(undefined);
    render(<PedidosDeAcesso sigla="LOP" aoMudar={async () => undefined} />);
    const botao = await screen.findByRole("button", { name: "Aprovar" });
    expect(botao).toBeDisabled();
    expect(screen.getByText(/pelo item LOP-3/)).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Papel para Ana Lima"), "leitor");
    await userEvent.click(botao);
    expect(aprovar).toHaveBeenCalledWith("LOP", "p1", "leitor");
  });
});

describe("textos da auditoria da Etapa 4", () => {
  const evento = (tipo: string, detalhes: Record<string, unknown>) =>
    ({ id: 1, ocorrido_em: "", tipo, ator: { id: "a", nome: "Ana", email: "", foto_url: null }, alvo: { id: "b", nome: "Bruno", email: "", foto_url: null }, detalhes, ip: null }) as Evento;

  it("descreve suporte, times e espaço aberto", () => {
    expect(descreverEvento(evento("suporte_iniciado", { espaco: "LOP", motivo: "Chamado 123" }))).toBe("Ana entrou para suporte no espaço LOP. Motivo: Chamado 123");
    expect(descreverEvento(evento("time_acesso_dado", { espaco: "LOP", time: "Jurídico", papel: "membro" }))).toBe("Ana deu ao time Jurídico acesso ao espaço LOP como Membro");
    expect(descreverEvento(evento("time_membro_adicionado", { time: "Jurídico" }))).toBe("Ana colocou Bruno no time Jurídico");
    expect(descreverEvento(evento("espaco_aberto", { espaco: "LOP" }))).toBe("Ana abriu o espaço LOP para toda a empresa");
    expect(descreverEvento(evento("membro_adicionado", { espaco: "LOP", papel: "leitor", por_pedido: true }))).toBe(
      "Ana aprovou o pedido de acesso e adicionou Bruno ao espaço LOP como Leitor",
    );
    expect(eventoDeAlerta("acao_em_suporte")).toBe(true);
  });
});
