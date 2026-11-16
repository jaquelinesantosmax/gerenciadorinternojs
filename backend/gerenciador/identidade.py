"""Entrada no sistema, independente de como a pessoa provou quem é.

Cada provedor de login (o login de teste hoje, o Google depois) só precisa entregar uma
IdentidadeExterna já confirmada. Todo o resto (domínio autorizado, cadastro automático,
usuário desativado, sessão e auditoria) acontece aqui, igual para qualquer provedor.
Por isso trocar o login de teste pelo Google não mexe no resto do sistema.
"""

import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import relogio, sessoes
from .auditoria import TipoEvento, registrar
from .erros import ErroDeRegra, LoginRecusado
from .modelos import DominioAutorizado, Usuario

_FORMATO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True)
class IdentidadeExterna:
    email: str
    nome: str
    provedor: str
    foto_url: str | None = None


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def dominio_do_email(email: str) -> str:
    return email.rsplit("@", 1)[-1]


def dominio_autorizado(db: Session, email: str) -> bool:
    return db.get(DominioAutorizado, dominio_do_email(email)) is not None


def entrar(
    db: Session, identidade: IdentidadeExterna, ip: str | None, agente: str | None
) -> tuple[Usuario, str]:
    """Valida a identidade, cadastra no primeiro acesso e abre a sessão. Devolve (usuário, token)."""
    email = normalizar_email(identidade.email)
    nome = identidade.nome.strip()

    if not _FORMATO_EMAIL.match(email):
        raise ErroDeRegra("Informe um e-mail válido.")

    if not dominio_autorizado(db, email):
        registrar(db, TipoEvento.LOGIN_FALHA, ip=ip, email=email, motivo="dominio_nao_autorizado",
                  provedor=identidade.provedor)
        db.commit()
        raise LoginRecusado(
            "dominio_nao_autorizado", "Use sua conta da Jusbrasil ou da Digesto para entrar."
        )

    usuario = db.scalar(select(Usuario).where(Usuario.email == email))
    agora = relogio.agora()

    if usuario is None:
        if not nome:
            raise ErroDeRegra("Informe o nome.")
        usuario = Usuario(email=email, nome=nome, foto_url=identidade.foto_url, criado_em=agora)
        db.add(usuario)
        db.flush()
        registrar(db, TipoEvento.CADASTRO_AUTOMATICO, ator_id=usuario.id, alvo_usuario_id=usuario.id,
                  ip=ip, provedor=identidade.provedor)
    elif identidade.provedor != "teste":
        # Nome e foto acompanham a conta Google. O login de teste não altera dados de quem já existe.
        usuario.nome = nome or usuario.nome
        usuario.foto_url = identidade.foto_url

    if not usuario.ativo:
        registrar(db, TipoEvento.LOGIN_FALHA, alvo_usuario_id=usuario.id, ip=ip, email=email,
                  motivo="usuario_desativado", provedor=identidade.provedor)
        db.commit()
        raise LoginRecusado(
            "usuario_desativado", "Seu acesso está desativado. Fale com o ADM da plataforma."
        )

    usuario.ultimo_acesso_em = agora
    token = sessoes.criar(db, usuario, ip, agente)
    registrar(db, TipoEvento.LOGIN, ator_id=usuario.id, alvo_usuario_id=usuario.id, ip=ip,
              provedor=identidade.provedor)
    db.commit()
    return usuario, token
