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
    response_UserInfo, # 新增
)
from controller.Cont_userCtrl import (
    createUser,
    checkAccount,
    LoginUser,
    ChangePassword,
    GetUserInfo, # 新增
)
from flask_jwt_extended import jwt_required, get_jwt_identity


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


# --- Pydantic Models for Change Password ---
class ChangePasswordForm(BaseModel):
    """更改密碼的請求模型"""

    old_password: str
    new_password: str


class ChangePasswordResponse(BaseModel):
    """更改密碼的成功回應模型"""

    message: str


# --- API Endpoint for Change Password ---
@userctrl.post(
    "/change-password",
    summary="更改當前使用者密碼",
    responses={200: ChangePasswordResponse, 401: {"description": "舊密碼不正確"}},
    security=[{"BearerAuth": []}],
)
@jwt_required()
def change_password(body: ChangePasswordForm):
    """
    更改目前已登入使用者的密碼。
    - 需要有效的 JWT Token。
    - 會驗證舊密碼是否正確。
    """
    current_user_account = get_jwt_identity()
    with get_db_session("default") as db:
        logic = ChangePassword(
            session=db,
            user_account=current_user_account,
            old_password=body.old_password,
            new_password=body.new_password,
        )
        return logic.run()


@userctrl.get(
    "/info",
    summary="獲取當前使用者資訊",
    responses={200: response_UserInfo},
    security=[{"BearerAuth": []}],
)
@jwt_required()
def get_user_info():
    """
    獲取目前已登入使用者的詳細資訊。
    - 需要有效的 JWT Token。
    """
    current_user_account = get_jwt_identity()
    with get_db_session("default") as db:
        logic = GetUserInfo(session=db, user_account=current_user_account)
        return logic.run()