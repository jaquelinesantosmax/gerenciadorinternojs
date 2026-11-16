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
    args = parser.parse_args(argv)

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
