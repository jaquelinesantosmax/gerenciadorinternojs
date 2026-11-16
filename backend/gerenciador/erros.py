"""Erros de regra de negócio. A API transforma cada um numa resposta com mensagem em português."""


class ErroDeRegra(Exception):
    status = 400

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class SemPermissao(ErroDeRegra):
    status = 403


class NaoEncontrado(ErroDeRegra):
    status = 404


class OperacaoNegada(ErroDeRegra):
    status = 409


class LoginRecusado(ErroDeRegra):
    status = 403

    def __init__(self, motivo: str, mensagem: str):
        super().__init__(mensagem)
        self.motivo = motivo
