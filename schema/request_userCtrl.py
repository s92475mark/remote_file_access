from pydantic import BaseModel, Field
from typing import Optional, List


class request_CreateUser(BaseModel):
    account: str = Field(..., description="User's account, must be unique")
    password: str = Field(..., description="User's password")
    storage_path: str = Field(..., description="User's storage path")
    name: str = Field(..., description="User's name")
    note: Optional[str] = Field(None, description="Optional note for the user")
    # role_ids: List[int] = Field(..., description="要關聯的角色ID列表, e.g., [1, 2, 5]")


class responst_CreateUser(BaseModel):
    id: int
    account: str
    name: str
    message: str = "User created successfully"
