from flask_openapi3 import APIBlueprint
from pydantic import BaseModel, Field
from flask import request

from typing import Optional
from util.db import get_db_session
from util.auth import permission_required
from schema.request_userCtrl import (
    request_CreateUser,
    response_CreateUser,
    response_account_check,
    request_account_check,
    request_Login,
    response_Login,
    response_UserInfo,
    UserInfoForAdmin,
    UserListResponse,
    request_UpdateUserRole,  # 新增
    response_UpdateUserRole,  # 新增
)
from controller.Cont_userCtrl import (
    createUser,
    checkAccount,
    LoginUser,
    ChangePassword,
    GetUserInfo,
    ListAllUsers,
    UpdateUserRole,  # 新增
)
from flask_jwt_extended import jwt_required, get_jwt_identity


class ErrorResponse(BaseModel):
    message: str
    detail: Optional[str] = None


userctrl = APIBlueprint("userctrl", __name__, url_prefix="/userCtrl")


@userctrl.post(
    "/createUser",
    summary="建新使用者v",
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
    responses={200: response_Login, 401: {"description": "帳號或密碼錯誤"}},
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


@userctrl.get(
    "/list-all",
    summary="獲取所有使用者列表",
    responses={200: UserListResponse},
    security=[{"BearerAuth": []}],
)
# @permission_required("admin:read")
def list_all_users():
    """
    獲取系統內所有使用者的列表。
    - 僅限管理者等級權限使用。
    """
    with get_db_session("default") as db:
        logic = ListAllUsers(session=db)
        users_rows = logic.run()
        # 將 SQLAlchemy Row 物件列表轉換為 Pydantic 模型列表
        user_list = [UserInfoForAdmin(**row._asdict()) for row in users_rows]
        return UserListResponse(users=user_list).model_dump()


@userctrl.patch(
    "/update-role",
    summary="修改使用者角色",
    responses={200: response_UpdateUserRole},
    security=[{"BearerAuth": []}],
)
@permission_required("role:update")
def update_user_role(body: request_UpdateUserRole):
    """
    修改指定使用者的角色。
    - 需要 `admin:update` 權限。
    - 操作者的權限等級必須高於或等於目標角色等級。
    - 無法修改自己的角色。
    """
    operator_account = get_jwt_identity()
    with get_db_session("default") as db:
        logic = UpdateUserRole(
            session=db,
            operator_account=operator_account,
            account_to_update=body.account,
            new_role_name=body.role_name,
        )
        updated_user = logic.run()
        return response_UpdateUser(
            id=updated_user.id,
            account=updated_user.account,
            user_name=updated_user.user_name,
        ).model_dump()
