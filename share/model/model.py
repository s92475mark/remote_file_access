from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Table, Column, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship

"""定義 model 相關"""


# pylint: disable=invalid-name
class Base(DeclarativeBase):
    """資料庫基礎格式"""

    id: Mapped[int] = mapped_column(primary_key=True)
    createTime: Mapped[datetime] = mapped_column(insert_default=datetime.now)
    updateTime: Mapped[datetime] = mapped_column(
        insert_default=datetime.now, onupdate=datetime.now
    )

    def __hash__(self) -> int:
        return hash((self.__class__.__name__, self.id))


# 角色與權限的關聯表 (Many-to-Many)
role_permissions_table = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
    Column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)

# 使用者與角色的關聯表 (Many-to-Many)
user_roles_table = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True),
)


class Permission(Base):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="權限代碼，用於程式判斷"
    )
    permission_name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="權限名稱，用於顯示"
    )

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, code='{self.code}')>"


class Role(Base):
    __tablename__ = "roles"

    role_name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="角色名稱"
    )

    # 建立與 Permission 的多對多關係
    permissions: Mapped[List[Permission]] = relationship(
        secondary=role_permissions_table, backref="roles", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.role_name}')>"


class User(Base):
    __tablename__ = "users"

    account: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(255), nullable=False)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # 建立與 Role 的多對多關係
    roles: Mapped[List[Role]] = relationship(
        secondary=user_roles_table, backref="users", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, account='{self.account}', name='{self.user_name}')>"
        )
