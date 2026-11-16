export function SemPermissao() {
  return (
    <div className="painel" style={{ maxWidth: 520 }}>
      <div style={{ fontWeight: 500 }}>Você não tem permissão para ver esta página.</div>
      <div className="legenda" style={{ marginTop: 4 }}>
        Se precisar, fale com o ADM da plataforma.
      </div>
    </div>
  );
}
