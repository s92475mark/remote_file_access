from functools import wraps
from typing import Set

from flask import abort
from flask_jwt_extended import get_jwt_identity, jwt_required

from util.db import get_db_session
from share.model.model import User


def get_user_permissions(user_account: str) -> Set[str]:
    """
    根據使用者帳號，從資料庫獲取該使用者的所有權限碼。
    透過遍歷使用者擁有的所有角色，並收集這些角色的所有權限。
    """
    with get_db_session() as db:
        # 根據帳號查詢使用者，並預先載入角色和權限以提高效率
        user = db.query(User).filter(User.account == user_account).first()

        # 如果找不到使用者，回傳一個空集合
        if not user:
            return set()

        # 使用集合 (set) 來自動處理重複的權限碼
        permissions_set = set()
        for role in user.roles:
            for perm in role.permissions:
                permissions_set.add(perm.code)

        return permissions_set


def permission_required(*required_perms: str):
    """
    一個裝飾器，用來檢查當前使用者是否擁有所有必要的權限。

    用法:
    @app.route("/some_route")
    @permission_required('user:read', 'user:create')
    def some_api_function():
        ...
    """

    def decorator(fn):
        @wraps(fn)
        @jwt_required()  # 首先確保使用者已登入且 JWT 有效
        def wrapper(*args, **kwargs):
            # 1. 從 JWT token 中獲取使用者身分 (我們存的是 account)
            current_user_account = get_jwt_identity()

            # 2. 獲取該使用者的所有權限
            user_perms = get_user_permissions(current_user_account)

            # 3. 檢查使用者是否擁有所有必要的權限
            #    set(required_perms) 是不是 user_perms 的子集
            if not set(required_perms).issubset(user_perms):
                # 如果權限不足，回傳 403 Forbidden 錯誤
                abort(
                    403,
                    description=f"Insufficient permissions. Requires: {', '.join(required_perms)}",
                )

            # 4. 如果權限檢查通過，執行原始的 API 函式
            return fn(*args, **kwargs)

        return wrapper

    return decorator
