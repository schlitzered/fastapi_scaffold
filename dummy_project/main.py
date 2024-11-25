from contextlib import asynccontextmanager
import logging
import random
import string
import sys
import time

from authlib.integrations.starlette_client import OAuth
import bonsai.asyncio
import httpx
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse
from fastapi_versionizer import Versionizer
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorDatabase
from starlette.middleware.sessions import SessionMiddleware
import uvicorn

import dummy_project.api
import dummy_project.oauth

from dummy_project.authorize import Authorize

from dummy_project.config import Settings
from dummy_project.config import Ldap as SettingsLdap
from dummy_project.config import OAuth as SettingsOAuth

from dummy_project.crud.credentials import CrudCredentials
from dummy_project.crud.ldap import CrudLdap
from dummy_project.crud.oauth import CrudOAuthGitHub
from dummy_project.crud.teams import CrudTeams
from dummy_project.crud.users import CrudUsers

from dummy_project.model.users import UserPost

from dummy_project.errors import ResourceNotFound


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log = setup_logging(
        settings.app.loglevel,
    )

    http = httpx.AsyncClient()

    ldap_pool = await setup_ldap(
        log=log,
        settings_ldap=settings.ldap,
    )

    log.info("adding routes")
    mongo_db = setup_mongodb(
        log=log,
        database=settings.mongodb.database,
        url=settings.mongodb.url,
    )

    oauth_providers = setup_oauth_providers(
        log=log,
        http=http,
        oauth_settings=settings.oauth,
    )

    crud_ldap = CrudLdap(
        log=log,
        ldap_base_dn=settings.ldap.basedn,
        ldap_bind_dn=settings.ldap.binddn,
        ldap_pool=ldap_pool,
        ldap_url=settings.ldap.url,
        ldap_user_pattern=settings.ldap.userpattern,
    )

    crud_teams = CrudTeams(
        log=log,
        coll=mongo_db["teams"],
    )
    await crud_teams.index_create()

    crud_users = CrudUsers(
        log=log,
        coll=mongo_db["users"],
        crud_ldap=crud_ldap,
    )
    await crud_users.index_create()

    crud_users_credentials = CrudCredentials(
        log=log,
        coll=mongo_db["users_credentials"],
    )
    await crud_users_credentials.index_create()

    authorize = Authorize(
        log=log,
        crud_teams=crud_teams,
        crud_users=crud_users,
        crud_users_credentials=crud_users_credentials,
    )

    api_router = dummy_project.api.Api(
        log=log,
        authorize=authorize,
        crud_ldap=crud_ldap,
        crud_teams=crud_teams,
        crud_users=crud_users,
        crud_users_credentials=crud_users_credentials,
        http=http,
    )
    app.include_router(api_router.router)
    # versionize(
    #     app=app,
    #     prefix_format="/api/v{major}",
    #     version_format="{major}",
    #     docs_url="/docs",
    #     redoc_url="/redoc",
    # )
    Versionizer(
        app=app,
        prefix_format="/api/v{major}",
        include_versions_route=True,
        semantic_version_format="{major}",
    ).versionize()

    oauth_router = dummy_project.oauth.Oauth(
        log=log, crud_users=crud_users, http=http, oauth_providers=oauth_providers
    )
    app.include_router(oauth_router.router)

    @app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
    def get_api_versions() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=f"{app.openapi_url}",
            title=f"{app.title}",
            swagger_ui_parameters={"defaultModelsExpandDepth": -1},
        )

    log.info("adding routes, done")
    await setup_admin_user(log=log, crud_users=crud_users)
    yield


async def setup_admin_user(log: logging.Logger, crud_users: CrudUsers):
    try:
        await crud_users.get(_id="admin", fields=["_id"])
    except ResourceNotFound:
        password = "".join(
            random.choice(string.ascii_letters + string.digits) for _ in range(20)
        )
        log.info(f"creating admin user with password {password}")
        await crud_users.create(
            _id="admin",
            payload=UserPost(
                admin=True, email="admin@example.com", name="admin", password=password
            ),
            fields=["_id"],
        )
        log.info("creating admin user, done")


async def setup_ldap(log: logging.Logger, settings_ldap: SettingsLdap):
    if not settings_ldap.url:
        log.info("ldap not configured")
        return
    log.info(f"setting up ldap with {settings_ldap.url} as a backend")
    if not settings_ldap.binddn:
        log.fatal("ldap binddn not configured")
        sys.exit(1)
    if not settings_ldap.password:
        log.fatal("ldap password not configured")
        sys.exit(1)
    client = bonsai.LDAPClient(settings_ldap.url)
    client.set_credentials("SIMPLE", settings_ldap.binddn, settings_ldap.password)
    pool = bonsai.asyncio.AIOConnectionPool(client=client, maxconn=30)
    await pool.open()
    return pool


def setup_logging(log_level):
    log = logging.getLogger("uvicorn")
    log.info(f"setting loglevel to: {log_level}")
    log.setLevel(log_level)
    return log


def setup_mongodb(log: logging.Logger, database: str, url: str) -> AsyncIOMotorDatabase:
    log.info("setting up mongodb client")
    pool = AsyncIOMotorClient(url)
    db = pool.get_database(database)
    log.info("setting up mongodb client, done")
    return db


def setup_oauth_providers(
    log: logging.Logger,
    http: httpx.AsyncClient,
    oauth_settings: dict["str", SettingsOAuth],
):
    oauth = OAuth()
    providers = {}
    for provider, config in oauth_settings.items():
        if config.type == "github":
            log.info(f"oauth setting up github provider with name {provider}")
            providers[provider] = CrudOAuthGitHub(
                log=log,
                http=http,
                backend_override=config.override,
                name=provider,
                oauth=oauth,
                scope=config.scope,
                client_id=config.client.id,
                client_secret=config.client.secret,
                authorize_url=config.url.authorize,
                access_token_url=config.url.accesstoken,
                userinfo_url=config.url.userinfo,
            )
    return providers

app = FastAPI(title="dummy_project", version="0.0.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=settings.app.secretkey, max_age=3600)


@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
