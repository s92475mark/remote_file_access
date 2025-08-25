from flask_openapi3 import APIBlueprint
from pydantic import BaseModel
from flask import request  # <-- 新增：匯入 request


# Use Pydantic for schema definition
class HelloSchema(BaseModel):
    message: str


# Use APIBlueprint
bp = APIBlueprint("aaa", __name__, url_prefix="/aaa")


# Use the integrated .get, .post, etc. decorators
@bp.get("/hello", summary="一個簡單的 Hello World API", responses={200: HelloSchema})
def hello():
    """Hello World API 的詳細描述"""
    # --- 新增：取得 Authorization Header ---
    auth_header = request.headers.get("Authorization")
    print(f"Received Authorization header: {auth_header}")
    # --- 結束 ---

    return {"message": f"Hello, World! Auth: {auth_header}"}
