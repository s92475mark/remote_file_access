from util.db import get_db_session
from sqlalchemy.orm import Session
from util.security import hash_password
from sqlalchemy import select
from share.define.model_enum import RoleName

from share.model.model import User, Role
from schema.request_userCtrl import request_CreateUser, responst_CreateUser


class createUser:
    """建立使用者"""

    def __init__(self, session: Session, body: request_CreateUser):
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

        get_roles_id = select(Role).where(Role.role_name == RoleName.lv3.value)
        q_get_roles_id = self.session.execute(get_roles_id).scalars().all()
        print("\033u", end="")
        print("q_get_roles_id", q_get_roles_id)

        new_user = User(
            account=self.body.account,
            password=hash_password(self.body.password),
            storage_path=self.body.storage_path,
            user_name=self.body.name,
            note=self.body.note,
            roles=q_get_roles_id,
        )

        self.session.add(new_user)
        self.session.commit()
        self.session.refresh(new_user)
        return responst_CreateUser(
            id=new_user.id,
            account=new_user.account,
            name=new_user.user_name,
            message="User created successfully",
        ).model_dump()
