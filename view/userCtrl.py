from flask_openapi3 import APIBlueprint
from pydantic import BaseModel, Field
from flask import request

from typing import Optional
from util.db import get_db_session
from schema.request_userCtrl import (
    request_CreateUser,
    response_CreateUser,
    response_account_check,
    request_account_check,
    request_Login,
    response_Login,
)
from controller.Cont_userCtrl import createUser, checkAccount, LoginUser


class ErrorResponse(BaseModel):
    message: str
    detail: Optional[str] = None


userctrl = APIBlueprint("userctrl", __name__, url_prefix="/userCtrl")


@userctrl.post(
    "/createUser",
    summary="建新使用者",
    responses={200: response_CreateUser},
)
def create_user(body: request_CreateUser):
    with get_db_session("default") as db:
        data = createUser(session=db, body=body)

        Outcome_dict = data.data()

        return Outcome_dict


@userctrl.get(
    "/accountCheck", summary="帳號命名驗證", responses={200: response_account_check}
)
def account_check(query: request_account_check):
    with get_db_session("default") as db:
        data = checkAccount(session=db, body=query)

        Outcome_dict = data.data()

        return Outcome_dict


@userctrl.post(
    "/login",
    summary="使用者登入",
    responses={
        200: response_Login,
        401: {"description": "帳號或密碼錯誤"}
    }
)
def user_login(body: request_Login):
    with get_db_session("default") as db:
        data = LoginUser(session=db, body=body)
        Outcome_dict = data.login()
        return Outcome_dict