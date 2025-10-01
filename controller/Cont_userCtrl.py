from operator import le
from util.db import get_db_session
from sqlalchemy.orm import Session
from util.security import hash_password
from sqlalchemy import select, func
from share.define.model_enum import RoleName

from util.global_variable import global_variable

from share.model.model import File, User, Role
from schema.request_userCtrl import (
    request_CreateUser,
    response_CreateUser,
    request_account_check,
    response_account_check,
    request_Login,
    response_Login,
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
        return response_account_check(account=True)


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
        from sqlalchemy import String, cast, func, select

        # 1. 建立一個子查詢，專門用來計算永久檔案的數量
        #    它會根據外部查詢的 User.id 來做關聯查詢
        perm_count_sq = (
            select(
                func.count(File.id).label("sub_permanent_file_count"),
                User.id.label("sub_user_id"),
            )
            .where(File.owner_id == User.id)  # 關聯外部的 User.id
            .where(File.is_permanent == True)
            .subquery()
        )

        # 2. 建立主查詢
        q = (
            select(
                User.account,
                User.user_name,
                func.sum(File.file_size).label("storage_usage"),  # 計算總大小
                func.count(File.id).label("file_count"),  # 計算總數量
                perm_count_sq.c.sub_permanent_file_count.label(
                    "permanent_file_count"
                ),  # 將子查詢作為一個欄位
            )
            .select_from(User)
            .join(perm_count_sq, perm_count_sq.c.sub_user_id == User.id, isouter=True) # 改為 LEFT OUTER JOIN
            .join(
                File, File.owner_id == User.id, isouter=True
            )  # 使用 outer join 以免使用者沒有檔案時查不到
            .where(User.account == self.user_account)  # 指定要查詢的使用者
            .group_by(User.id)  # 根據使用者 ID 分組
        )

        # 3. 執行查詢並取得結果
        result = self.session.execute(q).first()

        if not result:
            abort(404, "User not found.")

        # 4. 組合回傳的字典
        return {
            "user_name": result.user_name,
            "account": result.account,
            "storage_usage": int(result.storage_usage)
            if result.storage_usage is not None
            else 0,
            "file_count": result.file_count,
            "permanent_file_count": result.permanent_file_count
            if result.permanent_file_count is not None
            else 0,
        }
