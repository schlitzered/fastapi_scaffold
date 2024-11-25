import logging

from fastapi import APIRouter
from fastapi import Request
from fastapi import HTTPException
from starlette.responses import RedirectResponse

import httpx

from dummy_project.crud.users import CrudUsers
from dummy_project.crud.oauth import CrudOAuth

from dummy_project.errors import ResourceNotFound
from dummy_project.errors import AuthenticationError

from dummy_project.model.common import MetaMulti
from dummy_project.model.oauth import OauthProviderGet
from dummy_project.model.oauth import OauthProviderGetMulti
from dummy_project.model.users import UserPut


class OauthAuthenticate:
    def __init__(
        self,
        log: logging.Logger,
        crud_users: CrudUsers,
        http: httpx.AsyncClient,
        oauth_providers: dict[str, CrudOAuth],
    ):
        self._crud_users = crud_users
        self._http = http
        self._log = log
        self._oauth_providers = oauth_providers
        self._router = APIRouter(
            prefix="/authenticate",
            tags=["authenticate"],
        )

        self.router.add_api_route(
            "/oauth",
            self.get_oauth_providers,
            response_model=OauthProviderGetMulti,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/oauth/{provider}/login",
            self.get_oauth_login,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/oauth/{provider}/auth",
            self.get_oauth_auth,
            methods=["GET"],
        )

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
    def oauth_providers(self):
        return self._oauth_providers

    @property
    def router(self):
        return self._router

    async def get_oauth_providers(self, request: Request):
        providers = list()
        for provider in self.oauth_providers.keys():
            providers.append(OauthProviderGet(id=provider))
        return OauthProviderGetMulti(
            result=providers, meta=MetaMulti(result_size=len(providers))
        )

    async def get_oauth_login(self, provider: str, request: Request):
        provider = self.oauth_providers.get(provider, None)
        if provider is None:
            raise HTTPException(status_code=404, detail="oauth provider not found")
        return await provider.oauth_login(request=request)

    async def get_oauth_auth(
        self,
        provider: str,
        request: Request,
    ):
        _provider = self.oauth_providers.get(provider, None)
        if _provider is None:
            raise HTTPException(status_code=404, detail="oauth provider not found")
        token = await _provider.oauth_auth(request=request)
        userinfo = await _provider.get_user_info(token=token["access_token"])
        login = userinfo["login"]
        try:
            user = await self.crud_users.get(_id=login, fields=["backend"])
            if user.backend != f"oauth:{provider}":
                if _provider.backend_override:
                    self.log.warning(
                        f"backend override: backend:{user.backend} -> oauth:{provider}"
                    )
                    await self.crud_users.update(
                        _id=login,
                        payload=UserPut(
                            backend=f"oauth{provider}",
                        ),
                        fields=["_id"],
                    )
                else:
                    self.log.error(
                        f"auth backend mismatch: {user.backend} != {provider}"
                    )
                    raise AuthenticationError(
                        msg="backend mismatch, please contact the administrator"
                    )
        except ResourceNotFound:
            await self.crud_users.create_external(
                _id=login,
                payload=UserPut(
                    admin=False,
                    email=userinfo["email"],
                    name=userinfo["name"],
                ),
                fields=["_id"],
                backend=f"oauth:{provider}",
            )
        request.session["username"] = login
        return RedirectResponse(url="/")
