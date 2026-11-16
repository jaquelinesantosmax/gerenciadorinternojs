"""Anexos (docs/decisoes-de-desenho.md):

- Limite padrão do Jira Cloud: 1 GB por arquivo, ajustável até 2 GB pelo ADM da plataforma. Sem bloqueio por tipo.
- Pré-visualização só de imagens comuns e PDF. HTML, SVG e executáveis sempre baixados, nunca abertos.
- Links de download temporários; só quem tem acesso ao item vê os anexos.
"""

import hashlib
import hmac
import mimetypes
import time
import uuid
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import relogio
from .armazenamento import ArquivoGrandeDemais, obter_armazenamento
from .auditoria import TipoEvento, registrar
from .config import obter_config
from .erros import ErroDeRegra, NaoEncontrado, SemPermissao
from .espacos import pode_no_espaco
from .modelos import Usuario
from .modelos_espacos import Espaco
from .modelos_itens import Anexo, ConfigPlataforma, HistoricoItem, Item
from .papeis import exigir

LIMITE_MAXIMO_MB = 2048
VALIDADE_LINK_SEGUNDOS = 10 * 60

# Assinatura dos primeiros bytes de cada formato que pode ser aberto no navegador.
# Conferir o conteúdo (e não só a extensão) evita que um arquivo disfarçado seja aberto como imagem.
_ASSINATURAS = {
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],
    "image/bmp": [b"BM"],
    "application/pdf": [b"%PDF-"],
}


def limite_mb(db: Session) -> int:
    config = db.get(ConfigPlataforma, "limite_anexo_mb")
    return int(config.valor) if config else 1024


def definir_limite(db: Session, ator: Usuario, mb: int, ip: str | None) -> None:
    exigir(db, ator, "definir_limite_anexos")
    if not 1 <= mb <= LIMITE_MAXIMO_MB:
        raise ErroDeRegra(f"O limite precisa ficar entre 1 MB e {LIMITE_MAXIMO_MB} MB (2 GB).")
    config = db.get(ConfigPlataforma, "limite_anexo_mb")
    anterior = limite_mb(db)
    if config is None:
        db.add(ConfigPlataforma(chave="limite_anexo_mb", valor=mb))
    else:
        config.valor = mb
    registrar(db, TipoEvento.LIMITE_ANEXOS_ALTERADO, ator_id=ator.id, ip=ip, de=anterior, para=mb)
    db.commit()


def _nome_seguro(nome: str) -> str:
    nome = nome.replace("\\", "/").split("/")[-1].strip().replace("\x00", "")
    return (nome or "arquivo")[:255]


def enviar(
    db: Session, ator: Usuario, item: Item, espaco: Espaco, nome_arquivo: str, conteudo: BinaryIO
) -> Anexo:
    if not pode_no_espaco(db, ator, espaco, "anexar"):
        raise SemPermissao("Você não tem permissão para anexar arquivos neste espaço.")
    nome = _nome_seguro(nome_arquivo)
    limite = limite_mb(db)
    armazenamento = obter_armazenamento()
    try:
        chave, tamanho = armazenamento.salvar(conteudo, limite * 1024 * 1024)
    except ArquivoGrandeDemais as erro:
        raise ErroDeRegra(f"{nome} passa do limite de {limite} MB por arquivo.") from erro
    tipo = mimetypes.guess_type(nome)[0] or "application/octet-stream"
    anexo = Anexo(item_id=item.id, nome_arquivo=nome, tipo_mime=tipo, tamanho=tamanho, chave_armazenamento=chave,
                  enviado_por_id=ator.id, enviado_em=relogio.agora())
    db.add(anexo)
    db.add(HistoricoItem(item_id=item.id, autor_id=ator.id, ocorrido_em=relogio.agora(), campo="Anexos",
                         valor_anterior=None, valor_novo=nome))
    db.commit()
    return anexo


def listar(db: Session, item: Item) -> list[Anexo]:
    return list(db.scalars(select(Anexo).where(Anexo.item_id == item.id, Anexo.excluido_em.is_(None))
                           .order_by(Anexo.enviado_em.desc())))


def buscar(db: Session, anexo_id: uuid.UUID) -> Anexo:
    anexo = db.get(Anexo, anexo_id)
    if anexo is None or anexo.excluido_em is not None:
        raise NaoEncontrado("Anexo não encontrado.")
    return anexo


def excluir(db: Session, ator: Usuario, item: Item, espaco: Espaco, anexo: Anexo, ip: str | None) -> None:
    """ADM do espaço exclui qualquer anexo; os demais, só os que enviaram."""
    pode = pode_no_espaco(db, ator, espaco, "excluir_qualquer_anexo") or (
        anexo.enviado_por_id == ator.id and pode_no_espaco(db, ator, espaco, "anexar")
    )
    if not pode:
        raise SemPermissao("Você só pode excluir os anexos que enviou.")
    anexo.excluido_em = relogio.agora()
    anexo.excluido_por_id = ator.id
    db.add(HistoricoItem(item_id=item.id, autor_id=ator.id, ocorrido_em=relogio.agora(), campo="Anexos",
                         valor_anterior=anexo.nome_arquivo, valor_novo=None))
    registrar(db, TipoEvento.ANEXO_EXCLUIDO, ator_id=ator.id, ip=ip, item=f"{espaco.sigla}-{item.numero}",
              arquivo=anexo.nome_arquivo)
    db.commit()
    obter_armazenamento().apagar(anexo.chave_armazenamento)


# --- Links temporários ------------------------------------------------------------------------

def _assinatura(anexo_id: uuid.UUID, expira: int) -> str:
    mensagem = f"{anexo_id}:{expira}".encode()
    return hmac.new(obter_config().segredo.encode(), mensagem, hashlib.sha256).hexdigest()


def link_temporario(anexo: Anexo, agora: float | None = None) -> str:
    expira = int((agora or time.time()) + VALIDADE_LINK_SEGUNDOS)
    return f"/api/anexos/{anexo.id}/conteudo?expira={expira}&assinatura={_assinatura(anexo.id, expira)}"


def link_valido(anexo_id: uuid.UUID, expira: int, assinatura: str, agora: float | None = None) -> bool:
    if expira < (agora or time.time()):
        return False
    return hmac.compare_digest(_assinatura(anexo_id, expira), assinatura)


def pode_abrir_no_navegador(anexo: Anexo) -> str | None:
    """Devolve o tipo para mostrar no navegador, ou None se o arquivo deve ser sempre baixado."""
    esperadas = _ASSINATURAS.get(anexo.tipo_mime)
    if not esperadas:
        return None
    inicio = obter_armazenamento().primeiros_bytes(anexo.chave_armazenamento, 16)
    if anexo.tipo_mime == "image/webp":
        return anexo.tipo_mime if inicio[:4] == b"RIFF" and inicio[8:12] == b"WEBP" else None
    return anexo.tipo_mime if any(inicio.startswith(a) for a in esperadas) else None
