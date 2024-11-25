import logging


from fastapi import APIRouter
from fastapi import Request
from fastapi_versionizer import api_version

import httpx

from dummy_project.authorize import Authorize
from dummy_project.crud.users import CrudUsers

from dummy_project.errors import AuthenticationError

from dummy_project.model.common import DataDelete
from dummy_project.model.authenticate import AuthenticateGetUser
from dummy_project.model.authenticate import AuthenticatePost


class ApiAuthenticate:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_users: CrudUsers,
        http: httpx.AsyncClient,
    ):
        self._authorize = authorize
        self._crud_users = crud_users
        self._http = http
        self._log = log
        self._router = APIRouter(
            prefix="/authenticate",
            tags=["authenticate"],
        )

        self.router.add_api_route(
            "", self.get, response_model=AuthenticateGetUser, methods=["GET"]
        )
        self.router.add_api_route(
            "",
            self.create,
            response_model=AuthenticateGetUser,
            methods=["POST"],
            status_code=201,
        )
        self.router.add_api_route(
            "", self.delete, response_model=DataDelete, methods=["DELETE"]
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_users(self):
        return self._crud_users

    @property
    def http(self):
        return self._http

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

    @api_version(1)
    async def get(self, request: Request):
        user = await self.authorize.get_user(request=request)
        if not user:
            raise AuthenticationError
        return {"user": user.id}

    @api_version(1)
    async def create(
        self,
        data: AuthenticatePost,
        request: Request,
    ):
        user = await self.crud_users.check_credentials(credentials=data)
        request.session["username"] = user
        return {"user": user}

    @api_version(1)
    async def delete(self, request: Request):
        request.session.clear()
        return {}
