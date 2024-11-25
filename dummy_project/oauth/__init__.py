import logging

import httpx
from fastapi import APIRouter

from dummy_project.oauth.authenticate import OauthAuthenticate
from dummy_project.crud.oauth import CrudOAuth
from dummy_project.crud.users import CrudUsers


class Oauth:
    def __init__(
        self,
        log: logging.Logger,
        crud_users: CrudUsers,
        http: httpx.AsyncClient,
        oauth_providers: dict[str, CrudOAuth],
    ):
        self._log = log
        self._router = APIRouter()

        self._authenticate = OauthAuthenticate(
            log=log, crud_users=crud_users, http=http, oauth_providers=oauth_providers
        )

        self.router.include_router(
            self._authenticate.router,
            prefix="/api",
            responses={404: {"description": "Not found"}},
        )

    @property
    def router(self):
        return self._router
