import socket
import typing
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

log_levels = typing.Literal[
    "CRITICAL", "FATAL", "ERROR", "WARN", "WARNING", "INFO", "DEBUG"
]


class App(BaseModel):
    loglevel: log_levels = "INFO"
    secretkey: str = "secret"
    host: str = "127.0.0.1"
    port: int = 8000


class Ldap(BaseModel):
    url: typing.Optional[str] = None
    basedn: typing.Optional[str] = None
    binddn: typing.Optional[str] = None
    password: typing.Optional[str] = None
    userpattern: typing.Optional[str] = None


class Mongodb(BaseModel):
    url: str = "mongodb://localhost:27017"
    database: str = "dummy_project"


class OAuthClient(BaseModel):
    id: str
    secret: str


class OAuthUrl(BaseModel):
    authorize: str
    accesstoken: str
    userinfo: typing.Optional["str"] = None


class OAuth(BaseModel):
    override: bool = False
    scope: str
    type: str
    client: OAuthClient
    url: OAuthUrl


class Settings(BaseSettings):
    app: App = App()
    ldap: Ldap = Ldap()
    mongodb: Mongodb = Mongodb()
    oauth: typing.Optional[dict[str, OAuth]] = {}
    model_config = SettingsConfigDict(env_file=".env", env_nested_delimiter="_")
