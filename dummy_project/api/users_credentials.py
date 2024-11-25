import logging
from typing import Set

from fastapi import APIRouter
from fastapi import Query
from fastapi import Request
from fastapi_versionizer import api_version

from dummy_project.authorize import Authorize

from dummy_project.crud.credentials import CrudCredentials
from dummy_project.crud.users import CrudUsers

from dummy_project.model.common import DataDelete
from dummy_project.model.common import sort_order_literal
from dummy_project.model.credentials import filter_list
from dummy_project.model.credentials import filter_literal
from dummy_project.model.credentials import sort_literal
from dummy_project.model.credentials import CredentialGet
from dummy_project.model.credentials import CredentialGetMulti
from dummy_project.model.credentials import CredentialPost
from dummy_project.model.credentials import CredentialPostResult
from dummy_project.model.credentials import CredentialPut


class ApiUsersCredentials:
    def __init__(
        self,
        log: logging.Logger,
        authorize: Authorize,
        crud_users: CrudUsers,
        crud_users_credentials: CrudCredentials,
    ):
        self._authorize = authorize
        self._crud_users = crud_users
        self._crud_users_credentials = crud_users_credentials
        self._log = log
        self._router = APIRouter(
            prefix="/users/{user_id}/credentials",
            tags=["users_credentials"],
        )

        self.router.add_api_route(
            "",
            self.create,
            response_model=CredentialPostResult,
            response_model_exclude_unset=True,
            methods=["POST"],
            status_code=201,
        )
        self.router.add_api_route(
            "",
            self.search,
            response_model=CredentialGetMulti,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{credential_id}",
            self.delete,
            response_model=DataDelete,
            response_model_exclude_unset=True,
            methods=["DELETE"],
        )
        self.router.add_api_route(
            "/{credential_id}",
            self.get,
            response_model=CredentialGet,
            response_model_exclude_unset=True,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/{credential_id}",
            self.update,
            response_model=CredentialGet,
            response_model_exclude_unset=True,
            methods=["PUT"],
        )

    @property
    def authorize(self):
        return self._authorize

    @property
    def crud_users(self):
        return self._crud_users

    @property
    def crud_users_credentials(self):
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
        data: CredentialPost,
        user_id: str,
        request: Request,
    ):
        if user_id == "_self":
            user = await self.authorize.get_user(request=request)
            user_id = user.id
        else:
            await self.authorize.require_admin(request=request)
        await self.crud_users.resource_exists(_id=user_id)
        return await self.crud_users_credentials.create(
            owner=user_id,
            payload=data,
        )

    @api_version(1)
    async def delete(
        self,
        user_id: str,
        credential_id: str,
        request: Request,
    ):
        if user_id == "_self":
            user = await self.authorize.get_user(request=request)
            user_id = user.id
        else:
            await self.authorize.require_admin(request=request)
        return await self.crud_users_credentials.delete(
            _id=credential_id, owner=user_id
        )

    @api_version(1)
    async def get(
        self,
        request: Request,
        user_id: str,
        credential_id: str,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        if user_id == "_self":
            user = await self.authorize.get_user(request=request)
            user_id = user.id
        else:
            await self.authorize.require_admin(request=request)
        return await self.crud_users_credentials.get(
            owner=user_id, _id=credential_id, fields=list(fields)
        )

    @api_version(1)
    async def search(
        self,
        request: Request,
        user_id: str,
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
        if user_id == "_self":
            user = await self.authorize.get_user(request=request)
            user_id = user.id
        else:
            await self.authorize.require_admin(request=request)
        result = await self._crud_users_credentials.search(
            owner=user_id,
            fields=list(fields),
            sort=sort,
            sort_order=sort_order,
            page=page,
            limit=limit,
        )
        return result

    @api_version(1)
    async def update(
        self,
        request: Request,
        user_id: str,
        credential_id: str,
        data: CredentialPut,
        fields: Set[filter_literal] = Query(default=filter_list),
    ):
        if user_id == "_self":
            user = await self.authorize.get_user(request=request)
            user_id = user.id
        else:
            await self.authorize.require_admin(request=request)
        return await self.crud_users_credentials.update(
            _id=credential_id, owner=user_id, payload=data, fields=list(fields)
        )
