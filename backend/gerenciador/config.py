"""Configuração lida de variáveis de ambiente com o prefixo GERENCIADOR_."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GERENCIADOR_")

    database_url: str = "postgresql+psycopg://gerenciador@localhost:5433/gerenciador"
    ambiente: str = "desenvolvimento"
    # Login de teste: só existe no desenvolvimento, até a credencial Google da empresa chegar.
    login_teste_habilitado: bool = False
    # Em produção (HTTPS) o cookie precisa ser marcado como seguro.
    cookie_seguro: bool = False
    sessao_dias: int = 15

    def validar(self) -> None:
        if self.login_teste_habilitado and self.ambiente != "desenvolvimento":
            raise RuntimeError("O login de teste só pode ser ligado no ambiente de desenvolvimento.")


@lru_cache
def obter_config() -> Config:
    return Config()
