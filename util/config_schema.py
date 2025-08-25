"""設定檔相關"""
from pydantic import BaseModel, Field
from typing import Optional, Dict  # Import Dict


class OpenApiInfo(BaseModel):
    """OpenApiInfo"""

    title: str = "My API"


class OpenApiServer(BaseModel):
    """OpenApiServer"""

    url: str = "http://localhost:5000"
    url1: str = "http://127.0.0.1:5000"


class OpenApi(BaseModel):
    """OpenAPI 相關"""

    INFO: OpenApiInfo = OpenApiInfo()
    BLUEPRINTS: list[str] = Field([], description="Blueprint 的目錄")
    SERVERS: list[OpenApiServer] = Field(
        [OpenApiServer()], description="OpenAPI 上面的 Servers 選擇"
    )


class Flask(BaseModel):
    """Flask 相關"""

    HOST: str = "0.0.0.0"
    PORT: int = 5000
    DEBUG: bool = True


class Database(BaseModel):
    """Database related settings"""

    SQLALCHEMY_DATABASE_URI: str = "sqlite:///project.db"


class FileConfig(BaseModel):
    """File related settings"""
    path: str


class Config(BaseModel):
    """設定檔相關"""

    FLASK: Optional[Flask] = Flask()
    OPENAPI: Optional[OpenApi] = OpenApi()
    DATABASES: Dict[str, Database] = {}
    FILE: FileConfig
