from click import Option
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any
from datetime import datetime


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
    download_url: str | None


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
    file_limit: str | int
    permanent_file_limit: str | int


class UserInfoForAdmin(BaseModel):
    """在管理者列表中顯示的單一使用者資訊 (包含統計)"""

    account: str
    name: str
    role_name: Optional[str] = None
    file_limit: str  # 明確指定為字串
    permanent_file_limit: str  # 明確指定為字串
    total_file: int
    total_file_size: int
    p_total_file: int
    p_sub_file_size: int

    @field_validator("file_limit", "permanent_file_limit", mode="before")
    @classmethod
    def format_limits_to_string(cls, v):
        if v == -1:
            return "∞"
        if v is None:
            return "N/A"  # 處理可能為 None 的情況
        return str(v)  # 將數字轉換為字串

    @field_validator(
        "total_file",
        "total_file_size",
        "p_total_file",
        "p_sub_file_size",
        mode="before",
    )
    @classmethod
    def default_to_zero(cls, v):
        return v if v is not None else 0


class UserListResponse(BaseModel):
    """使用者列表的回應模型"""

    users: List[UserInfoForAdmin]


class request_UpdateUserRole(BaseModel):
    """修改使用者角色的請求模型"""

    account: str = Field(..., description="要修改的使用者帳號")
    role_name: str = Field(..., description="要賦予的新角色名稱")


class response_UpdateUserRole(BaseModel):
    """修改使用者角色的回應模型"""

    id: int
    account: str
    user_name: str
    message: str = "User role updated successfully"
