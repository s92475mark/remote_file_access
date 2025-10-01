from click import Option
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime  # 新增這一行


class request_CreateUser(BaseModel):
    account: str = Field(..., description="User's account, must be unique")
    password: str = Field(..., description="User's password")
    storage_path: str = Field(..., description="User's storage path")
    name: str = Field(..., description="User's name")
    note: Optional[str] = Field(None, description="Optional note for the user")
    # role_ids: List[int] = Field(..., description="要關聯的角色ID列表, e.g., [1, 2, 5]")


class response_CreateUser(BaseModel):
    id: int
    account: str
    name: str
    message: str = "User created successfully"


class request_Login(BaseModel):
    """登入請求模型"""

    account: str = Field(..., description="使用者帳號")
    password: str = Field(..., description="使用者密碼")


class FileInfo(BaseModel):
    """單一檔案的資訊模型"""

    id: int
    filename: str
    size_bytes: int
    upload_time: datetime
    del_time: datetime | None
    is_permanent: bool
    safe_filename: str
    share_token: str | None


class response_Login(BaseModel):
    """成功登入的回應模型"""

    access_token: str = Field(..., description="JWT Access Token")
    user_name: str = Field(..., description="使用者名稱")
    level: int | None = Field(..., description="使用者等級")
    level_name: str = Field(..., description="使用者等級名稱")


class request_account_check(BaseModel):
    account: str


class response_account_check(BaseModel):
    account: bool


class FileListStats(BaseModel):
    file_count: int
    permanent_file_count: int


class FileListLimits(BaseModel):
    file_limit: str | int
    permanent_file_limit: str | int


class FileListResponse(BaseModel):
    """檔案列表的回應模型"""

    files: list[FileInfo]
    stats: FileListStats
    limits: FileListLimits


class response_UserInfo(BaseModel):
    """使用者詳細資訊的回應模型"""
    user_name: str
    account: str
    storage_usage: int
    file_count: int
    permanent_file_count: int
