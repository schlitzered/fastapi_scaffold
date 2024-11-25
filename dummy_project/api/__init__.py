import logging

import httpx
from fastapi import APIRouter

from dummy_project.authorize import Authorize

from dummy_project.api.authenticate import ApiAuthenticate
from dummy_project.api.teams import ApiTeams
from dummy_project.api.users import ApiUsers
from dummy_project.api.users_credentials import ApiUsersCredentials

from dummy_project.crud.credentials import CrudCredentials
from dummy_project.crud.ldap import CrudLdap
from dummy_project.crud.teams import CrudTeams
from dummy_project.crud.users import CrudUsers


class Api:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_ldap: CrudLdap,
        crud_teams: CrudTeams,
        crud_users: CrudUsers,
        crud_users_credentials: CrudCredentials,
        http: httpx.AsyncClient,
    ):
        self._log = log
        self._router = APIRouter()

        self.router.include_router(
            ApiAuthenticate(
                log=log,
                authorize=authorize,
                crud_users=crud_users,
                http=http,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ApiTeams(
                log=log,
                authorize=authorize,
                crud_teams=crud_teams,
                crud_ldap=crud_ldap,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ApiUsers(
                log=log,
                authorize=authorize,
                crud_teams=crud_teams,
                crud_users=crud_users,
                crud_users_credentials=crud_users_credentials,
            ).router,
            responses={404: {"description": "Not found"}},
        )

        self.router.include_router(
            ApiUsersCredentials(
                log=log,
                authorize=authorize,
                crud_users=crud_users,
                crud_users_credentials=crud_users_credentials,
            ).router,
            responses={404: {"description": "Not found"}},
        )

    @property
    def router(self):
        return self._router
