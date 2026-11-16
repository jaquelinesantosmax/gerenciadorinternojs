"""Comandos de instalação.

Cadastrar o primeiro ADM da plataforma:
    python -m gerenciador.cli criar-adm --email nome@jusbrasil.com.br --nome "Nome Sobrenome"
"""

import argparse
import sys

from .banco import nova_sessao
from .erros import ErroDeRegra
from .papeis import cadastrar_adm_instalacao


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="gerenciador")
    sub = parser.add_subparsers(dest="comando", required=True)
    adm = sub.add_parser("criar-adm", help="Cadastra um ADM da plataforma (uso na instalação)")
    adm.add_argument("--email", required=True)
    adm.add_argument("--nome", required=True)
    sub.add_parser("preparar-dados", help="Completa dados que dependem das regras (roda depois das migrações)")
    args = parser.parse_args(argv)

    if args.comando == "preparar-dados":
        from .preparar_dados import preparar

        with nova_sessao() as db:
            contagem = preparar(db)
        print(f"Dados conferidos: {contagem['espacos']} espaço(s), {contagem['paineis']} painel(is) e "
              f"{contagem['itens']} item(ns) completados.")
        return 0

    if args.comando == "criar-adm":
        with nova_sessao() as db:
            try:
                usuario = cadastrar_adm_instalacao(db, args.email, args.nome)
            except ErroDeRegra as erro:
                print(erro.mensagem, file=sys.stderr)
                return 1
        print(f"Pronto: {usuario.nome} ({usuario.email}) é ADM da plataforma.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
