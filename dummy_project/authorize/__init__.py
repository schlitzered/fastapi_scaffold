import logging
import typing

from fastapi import Request

from dummy_project.crud.users import CrudUsers
from dummy_project.crud.credentials import CrudCredentials
from dummy_project.crud.teams import CrudTeams

from dummy_project.errors import AdminError
from dummy_project.errors import CredentialError
from dummy_project.errors import ResourceNotFound
from dummy_project.errors import SessionCredentialError

from dummy_project.model.users import UserGet


class Authorize:
    def __init__(
        self,
        log: logging.Logger,
        crud_teams: CrudTeams,
        crud_users: CrudUsers,
        crud_users_credentials: CrudCredentials,
    ):
        self._crud_teams = crud_teams
        self._crud_users = crud_users
        self._crud_users_credentials = crud_users_credentials
        self._log = log

    @property
    def crud_teams(self) -> CrudTeams:
        return self._crud_teams

    @property
    def crud_users(self) -> CrudUsers:
        return self._crud_users

    @property
    def crud_users_credentials(self):
        return self._crud_users_credentials

    @property
    def log(self):
        return self._log

    async def get_user(self, request: Request) -> UserGet:
        user = self.get_user_from_session(request=request)
        if not user:
            user = await self.get_user_from_credentials(request=request)
        if not user:
            raise SessionCredentialError
        user = await self.crud_users.get(_id=user, fields=["id", "admin"])
        user = await self.get_user_override(request=request, user=user)
        return user

    async def get_user_override(self, request: Request, user: UserGet) -> UserGet:
        if not user.admin:
            return user
        x_user_override = request.headers.get("x-user-override", None)
        if not x_user_override:
            return user
        try:
            _user = await self.crud_users.get(
                _id=x_user_override, fields=["id", "admin"]
            )
            self.log.info(f"user {user.id} assumes user {_user.id}")
            return _user
        except ResourceNotFound:
            self.log.error(f"cannot assume user {x_user_override}, user not found")
            raise SessionCredentialError

    async def get_user_from_credentials(self, request: Request) -> UserGet:
        try:
            self.log.info("trying to get user from credentials")
            user = await self.crud_users_credentials.check_credential(request=request)
            self.log.debug(f"received user {user} from credentials")
            return user
        except (CredentialError, ResourceNotFound):
            self.log.debug("trying to get user from credentials, failed")

    def get_user_from_session(self, request: Request) -> typing.Optional[str]:
        self.log.debug("trying to get user from session")
        user = request.session.get("username", None)
        if user is None:
            self.log.debug("trying to get user from session, failed")
        else:
            self.log.debug(f"received user {user} from session")
            return user

    async def require_admin(self, request, user=None) -> UserGet:
        if not user:
            user = await self.get_user(request=request)
        if not user.admin:
            raise AdminError
        return user

    async def require_user(self, request) -> UserGet:
        user = await self.get_user(request)
        return user
