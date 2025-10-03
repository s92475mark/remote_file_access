from operator import le
from util.db import get_db_session
from sqlalchemy.orm import Session, aliased
from util.security import hash_password
from sqlalchemy import label, select, func
from share.define.model_enum import RoleName, permanent_file

from util.global_variable import global_variable

from share.model.model import File, User, Role
from schema.request_userCtrl import (
    request_CreateUser,
    response_CreateUser,
    request_account_check,
    response_account_check,
    request_Login,
    response_Login,
    response_UserInfo,
)
from util.security import verify_password
from flask import abort
from flask_jwt_extended import create_access_token
import os


class checkAccount:
    """檢查帳號是否可行"""

    def __init__(self, session: Session, body: request_account_check):
        self.session = session
        self.body = body

    def data(self):
        # 檢查帳號是否存在
        existing_user = (
            self.session.query(User).filter(User.account == self.body.account).first()
        )
        if existing_user:
            return {
                "message": "Account already exists",
                "detail": f"Account '{self.body.account}' is already taken.",
            }, 409
        return response_account_check(account=True).model_dump()


class createUser:
    """建立使用者"""

    def __init__(self, session: Session, body: request_CreateUser):
        self.session = session
        self.body = body

    def data(self):
        get_roles_id = select(Role).where(Role.role_name == RoleName.lv3.value)
        q_get_roles_id = self.session.execute(get_roles_id).scalars().all()
        # --- 建立使用者專屬資料夾 ---
        base_path = global_variable.config.FILE.path
        user_storage_path = os.path.join(base_path, self.body.account)
        os.makedirs(user_storage_path, exist_ok=True)

        new_user = User(
            account=self.body.account,
            password=hash_password(self.body.password),
            storage_path=user_storage_path,  # <-- 使用新建的資料夾路徑
            user_name=self.body.name,
            note=self.body.note,
            roles=q_get_roles_id,
        )

        self.session.add(new_user)
        self.session.commit()
        self.session.refresh(new_user)
        return response_CreateUser(
            id=new_user.id,
            account=new_user.account,
            name=new_user.user_name,
            message="User created successfully",
        ).model_dump()


class LoginUser:
    """登入驗證"""

    def __init__(self, session: Session, body: request_Login):
        self.session = session
        self.body = body

    def login(self):
        user = (
            self.session.query(User).filter(User.account == self.body.account).first()
        )

        # 驗證使用者是否存在，以及密碼是否正確
        if not user or not verify_password(self.body.password, user.password):
            abort(401, description="帳號或密碼錯誤")

        # 密碼驗證成功，產生 JWT
        access_token = create_access_token(identity=user.account)

        # 尋找 ID 最小的角色
        user_level = None  # 預設等級 ID
        user_level_name = "No Role Assigned"  # 預設等級名稱

        if user.roles:
            # 使用 min()函式和 lambda 來找到 id 最小的 role 物件
            min_id_role = min(user.roles, key=lambda role: role.level)
            user_level = min_id_role.level
            user_level_name = min_id_role.role_name

        return response_Login(
            access_token=access_token,
            user_name=user.user_name,
            level=user_level,
            level_name=user_level_name,
        ).model_dump()


class ChangePassword:
    """更改使用者密碼"""

    def __init__(
        self, session: Session, user_account: str, old_password: str, new_password: str
    ):
        self.session = session
        self.user_account = user_account
        self.old_password = old_password
        self.new_password = new_password

    def run(self):
        # 1. 查詢使用者
        user = (
            self.session.query(User)
            .filter(User.account == self.user_account)
            .one_or_none()
        )
        if not user:
            # 理論上，因為有 JWT 保護，所以不會發生這種情況
            abort(404, "User not found.")

        # 2. 驗證舊密碼
        if not verify_password(self.old_password, user.password):
            abort(401, "舊密碼不正確")

        # 3. 將新密碼雜湊化並更新
        user.password = hash_password(self.new_password)
        self.session.commit()

        return {"message": "密碼已成功更新"}


class GetUserInfo:
    """獲取使用者詳細資訊的核心邏輯"""

    def __init__(self, session: Session, user_account: str):
        self.session = session
        self.user_account = user_account

    def run(self):
        from sqlalchemy import String, cast, func, select, case

        # 查詢使用者、統計資料和權限
        result = (
            self.session.query(
                User.account,
                User.user_name,
                func.count(File.id).label("file_count"),
                func.sum(File.file_size).label("storage_usage"),
                func.sum(case((File.is_permanent == True, 1), else_=0)).label(
                    "permanent_file_count"
                ),
                Role.file_limit,
                Role.permanent_file_limit,
            )
            .select_from(User)
            .outerjoin(User.roles)  # 使用 outerjoin 以免使用者沒有角色
            .outerjoin(File, File.owner_id == User.id)  # 使用 outerjoin 以免使用者沒有檔案
            .filter(User.account == self.user_account)
            .group_by(User.id, Role.id)
            .order_by(Role.level.asc())
            .first()
        )

        if not result:
            # 如果上面的查詢找不到結果(例如一個完全沒有角色的新使用者)，做一個備用查詢
            user = (
                self.session.query(User)
                .filter(User.account == self.user_account)
                .one_or_none()
            )
            if not user:
                abort(404, "User not found.")
            return {
                "user_name": user.user_name,
                "account": user.account,
                "storage_usage": 0,
                "file_count": 0,
                "permanent_file_count": 0,
                "file_limit": "N/A",
                "permanent_file_limit": "N/A",
            }

        # 組合回傳的字典
        return {
            "user_name": result.user_name,
            "account": result.account,
            "storage_usage": int(result.storage_usage)
            if result.storage_usage is not None
            else 0,
            "file_count": result.file_count,
            "permanent_file_count": result.permanent_file_count,
            "file_limit": "∞" if result.file_limit == -1 else result.file_limit,
            "permanent_file_limit": "∞"
            if result.permanent_file_limit == -1
            else result.permanent_file_limit,
        }


class ListAllUsers:
    """獲取所有使用者列表的核心邏輯"""

    def __init__(self, session: Session):
        self.session = session

    def run(self):
        file_count = (
            select(
                User.id.label("sub_user_id"),
                func.count(File.id).label("sub_file_count"),
                func.sum(File.file_size).label("sub_file_size"),
            )
            .join(File, File.owner_id == User.id)
            .group_by(User.id)
        )
        sub_file_count = file_count.subquery()
        p_file_count = file_count.where(
            File.is_permanent == permanent_file.is_permanent.value
        )
        sub_p_file_count = p_file_count.subquery()

        query = (
            select(
                User.account.label("account"),
                User.user_name.label("name"),
                Role.role_name.label("role_name"),
                Role.file_limit.label("file_limit"),  # 檔案上限
                Role.permanent_file_limit.label("permanent_file_limit"),  # 永久檔案數量上限
                sub_file_count.c.sub_file_count.label("total_file"),  # 擁有檔案數量
                sub_file_count.c.sub_file_size.label("total_file_size"),  # 擁有檔案大小
                sub_p_file_count.c.sub_file_count.label("p_total_file"),  # 擁有的永久檔案數量
                sub_p_file_count.c.sub_file_size.label("p_sub_file_size"),  # 擁有的永久檔案大小
            )
            .select_from(User)
            .join(User.roles.of_type(Role))
            .outerjoin(sub_file_count, sub_file_count.c.sub_user_id == User.id)
            .outerjoin(sub_p_file_count, sub_p_file_count.c.sub_user_id == User.id)
        )

        users = self.session.execute(query).all()
        return users
