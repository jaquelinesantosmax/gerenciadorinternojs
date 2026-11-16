import { iniciais } from "@/lib/formato";

export function Avatar({
  nome,
  fotoUrl,
  claro = false,
  tamanho = 32,
}: {
  nome: string;
  fotoUrl?: string | null;
  claro?: boolean;
  tamanho?: number;
}) {
  return (
    <span
      className={`avatar${claro ? " avatar-claro" : ""}`}
      style={{ width: tamanho, height: tamanho, fontSize: Math.round(tamanho * 0.38) }}
      aria-hidden="true"
    >
      {fotoUrl ? <img src={fotoUrl} alt="" referrerPolicy="no-referrer" /> : iniciais(nome)}
    </span>
  );
}
