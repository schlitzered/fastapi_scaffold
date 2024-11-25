import logging
from typing import Set

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request
from fastapi_versionizer import api_version

from dummy_project.authorize import Authorize

from dummy_project.crud.teams import CrudTeams
from dummy_project.crud.users import CrudUsers
from dummy_project.crud.credentials import CrudCredentials

from dummy_project.model.common import DataDelete
from dummy_project.model.common import sort_order_literal
from dummy_project.model.users import filter_list
from dummy_project.model.users import filter_literal
from dummy_project.model.users import sort_literal
from dummy_project.model.users import UserGet
from dummy_project.model.users import UserGetMulti
from dummy_project.model.users import UserPost
from dummy_project.model.users import UserPut


class ApiUsers:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_teams: CrudTeams,
        crud_users: CrudUsers,
        crud_users_credentials: CrudCredentials,
    ):
        self._authorize = authorize
        self._crud_teams = crud_teams
        self._crud_users = crud_users
        self._crud_users_credentials = crud_users_credentials
        self._log = log
        self._router = APIRouter(
            prefix="/users",
            tags=["users"],
        )

        self.router.add_api_route(
            "",
            self.search,
            response_model=UserGetMulti,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{user_id}",
            self.create,
            response_model=UserGet,
            response_model_exclude_unset=True,
            methods=["POST"],
            status_code=201,
        )
        self.router.add_api_route(
            "/{user_id}",
            self.delete,
            response_model=DataDelete,
            response_model_exclude_unset=True,
            methods=["DELETE"],
        )
        self.router.add_api_route(
            "/{user_id}",
            self.get,
            response_model=UserGet,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{user_id}",
            self.update,
            response_model=UserGet,
            response_model_exclude_unset=True,
            methods=["PUT"],
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_teams(self):
        return self._crud_teams

    @property
    def crud_users(self):
        return self._crud_users

    @property
    def curd_users_credentials(self):
        return self._crud_users_credentials

    @property
    def log(self):
        return self._log

    @property
    def router(self):
        return self._router

    @api_version(1)
    async def create(
        self,
        request: Request,
        data: UserPost,
        user_id: str,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        await self.authorize.require_admin(request=request)
        return await self.crud_users.create(
            _id=user_id, payload=data, fields=list(fields)
        )

    @api_version(1)
    async def delete(self, request: Request, user_id: str):
        await self.authorize.require_admin(request=request)
        await self.crud_users.delete_mark(_id=user_id)
        await self.curd_users_credentials.delete_all_from_owner(owner=user_id)
        await self.crud_teams.delete_user_from_teams(user_id=user_id)
        return await self.crud_users.delete(_id=user_id)

    @api_version(1)
    async def get(
        self,
        user_id: str,
        request: Request,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        if user_id == "_self":
            user_id = await self.authorize.get_user(request=request)
            user_id = user_id.id
        else:
            await self.authorize.require_admin(request=request)
        return await self.crud_users.get(_id=user_id, fields=list(fields))

    @api_version(1)
    async def search(
        self,
        request: Request,
        user_id: str = Query(description="filter: regular_expressions", default=None),
        fields: Set[filter_literal] = Query(default=filter_list),
        sort: sort_literal = Query(default="id"),
        sort_order: sort_order_literal = Query(default="ascending"),
        page: int = Query(default=0, ge=0, description="pagination index"),
        limit: int = Query(
            default=10,
            ge=10,
            le=1000,
            description="pagination limit, min value 10, max value 1000",
        ),
    ):
        await self.authorize.require_admin(request=request)
        return await self.crud_users.search(
            _id=user_id,
            fields=list(fields),
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )

    @api_version(1)
    async def update(
        self,
        data: UserPut,
        user_id: str,
        request: Request,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        if user_id == "_self":
            user_id = await self.authorize.get_user(request=request)
            user_id = user_id.id
            data.admin = None
        else:
            await self.authorize.require_admin(request=request)
        return await self.crud_users.update(
            _id=user_id, payload=data, fields=list(fields)
        )
