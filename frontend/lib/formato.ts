// Formatação de datas (sempre no horário de Brasília) e nomes.

const FUSO = "America/Sao_Paulo";

const dataHora = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

const soData = new Intl.DateTimeFormat("pt-BR", {
  timeZone: FUSO,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

/** "16/11/2026, 09:58" */
export function formatarDataHora(iso: string | null | undefined): string {
  if (!iso) return "—";
  return dataHora.format(new Date(iso));
}

/** "16/11/2026" */
export function formatarData(iso: string | null | undefined): string {
  if (!iso) return "—";
  return soData.format(new Date(iso));
}

/** Iniciais para o avatar: "Maria da Silva" → "MS". */
export function iniciais(nome: string): string {
  const partes = nome
    .trim()
    .split(/\s+/)
    .filter((p) => p.length > 2 || /^[A-ZÀ-Ú]/.test(p));
  if (partes.length === 0) return "?";
  const primeira = partes[0][0];
  const ultima = partes.length > 1 ? partes[partes.length - 1][0] : "";
  return (primeira + ultima).toUpperCase();
}

export function primeiroNome(nome: string): string {
  return nome.trim().split(/\s+/)[0] ?? nome;
}
