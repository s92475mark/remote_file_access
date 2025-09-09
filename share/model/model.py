from datetime import datetime
from typing import Optional, List

from sqlalchemy import String, Table, Column, ForeignKey, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship

"""定義 model 相關"""


class Base(DeclarativeBase):
    """資料庫基礎格式"""

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="權限名稱，用於顯示")

    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, code='{self.code}')>"


class Role(Base):
    __tablename__ = "roles"

    role_name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, comment="角色名稱"
    )
    level: Mapped[int] = mapped_column(comment="角色等級，有0 ~ 4，0為最高權限")
    file_limit: Mapped[int] = mapped_column(comment="總檔案數量限制 (-1 為無限)")
    permanent_file_limit: Mapped[int] = mapped_column(comment="永久檔案數量限制 (-1 為無限)")
    file_lifetime_days: Mapped[int] = mapped_column(comment="檔案生命週期(天)")

    permissions: Mapped[List[Permission]] = relationship(
        secondary=role_permissions_table, backref="roles", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.role_name}')>"


class File(Base):
    __tablename__ = "files"

    filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始檔名")
    storage_path: Mapped[str] = mapped_column(
        String(512), unique=True, nullable=False, comment="儲存在伺服器上的路徑或檔名"
    )
    file_size: Mapped[int] = mapped_column(comment="檔案大小 (bytes)")
    is_permanent: Mapped[bool] = mapped_column(default=False, comment="是否為永久檔案")
    expiry_time: Mapped[Optional[datetime]] = mapped_column(comment="檔案過期時間 (非永久檔案才有)")
    share_token: Mapped[Optional[str]] = mapped_column(
        String(64), unique=True, index=True, comment="公開分享連結的 token"
    )

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    owner: Mapped["User"] = relationship(back_populates="files")

    def __repr__(self) -> str:
        return f"<File(id={self.id}, filename='{self.filename}')>"


class User(Base):
    __tablename__ = "users"

    account: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(255), nullable=False)
    user_name: Mapped[str] = mapped_column(String(100), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    roles: Mapped[List[Role]] = relationship(
        secondary=user_roles_table, backref="users", lazy="selectin"
    )
    # 新增的檔案關聯
    files: Mapped[List["File"]] = relationship(back_populates="owner")

    def __repr__(self) -> str:
        return (
            f"<User(id={self.id}, account='{self.account}', name='{self.user_name}')>"
        )
