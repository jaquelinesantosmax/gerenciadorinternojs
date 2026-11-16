import type { Evento } from "./api";
import { formatarData, formatarDataHora, iniciais, primeiroNome } from "./formato";
import { descreverEvento, eventoDeAlerta } from "./textos";

const ana = { id: "1", nome: "Ana Lima", email: "ana@jusbrasil.com.br", foto_url: null };
const bruno = { id: "2", nome: "Bruno Reis", email: "bruno@jusbrasil.com.br", foto_url: null };

function evento(tipo: string, detalhes: Record<string, unknown> = {}, ator = ana, alvo = bruno): Evento {
  return { id: 1, ocorrido_em: "2026-11-16T12:58:00Z", tipo, ator, alvo, detalhes, ip: null };
}

describe("descreverEvento", () => {
  it("descreve mudanças de papel com quem fez e quem recebeu", () => {
    expect(descreverEvento(evento("papel_concedido", { papel: "gestor" }))).toBe("Ana Lima deu o papel Gestor a Bruno Reis");
    expect(descreverEvento(evento("papel_revogado", { papel: "adm_plataforma" }))).toBe(
      "Ana Lima tirou o papel ADM da plataforma de Bruno Reis",
    );
  });

  it("descreve entradas e recusas", () => {
    expect(descreverEvento(evento("login", { provedor: "teste" }))).toBe("Ana Lima entrou pelo login de teste");
    expect(descreverEvento(evento("login", { provedor: "google" }))).toBe("Ana Lima entrou");
    const recusa = { ...evento("login_falha", { email: "x@gmail.com", motivo: "dominio_nao_autorizado" }), ator: null, alvo: null };
    expect(descreverEvento(recusa)).toBe("Entrada recusada para x@gmail.com: domínio não autorizado");
  });

  it("conta as sessões encerradas na desativação", () => {
    expect(descreverEvento(evento("usuario_desativado", { sessoes_encerradas: 0 }))).toBe(
      "Ana Lima desativou Bruno Reis (nenhuma sessão aberta)",
    );
    expect(descreverEvento(evento("usuario_desativado", { sessoes_encerradas: 1 }))).toBe(
      "Ana Lima desativou Bruno Reis (1 sessão encerrada)",
    );
    expect(descreverEvento(evento("usuario_desativado", { sessoes_encerradas: 3 }))).toBe(
      "Ana Lima desativou Bruno Reis (3 sessões encerradas)",
    );
  });

  it("cadastro na instalação não tem autor", () => {
    expect(descreverEvento({ ...evento("adm_instalacao"), ator: null })).toBe(
      "Bruno Reis foi cadastrado como ADM da plataforma na instalação",
    );
  });

  it("tipo desconhecido não quebra a tela", () => {
    expect(descreverEvento(evento("novo_tipo"))).toBe("novo_tipo");
  });

  it("destaca recusas e desativações", () => {
    expect(eventoDeAlerta("login_falha")).toBe(true);
    expect(eventoDeAlerta("usuario_desativado")).toBe(true);
    expect(eventoDeAlerta("login")).toBe(false);
  });
});

describe("formato", () => {
  it("mostra datas no horário de Brasília", () => {
    expect(formatarDataHora("2026-11-16T12:58:00Z")).toBe("16/11/2026, 09:58");
    expect(formatarData("2026-11-17T01:00:00Z")).toBe("16/11/2026");
    expect(formatarDataHora(null)).toBe("—");
  });

  it("monta iniciais ignorando partículas", () => {
    expect(iniciais("Maria da Silva")).toBe("MS");
    expect(iniciais("Ana")).toBe("A");
    expect(iniciais("  ")).toBe("?");
    expect(primeiroNome("Jaqueline Santos")).toBe("Jaqueline");
  });
});
