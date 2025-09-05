from flask_openapi3 import APIBlueprint, Tag
from flask_openapi3.models.file import FileStorage
from pydantic import BaseModel, Field
from flask_jwt_extended import get_jwt_identity

from util.db import get_db_session
from util.auth import permission_required
from controller.Cont_fileCtrl import UploadFile
from datetime import date, datetime, time

# --- API 藍圖和標籤定義 ---
tag = Tag(name="File Operations", description="檔案相關操作")
filectrl = APIBlueprint("filectrl", __name__, url_prefix="/files", abp_tags=[tag])


# --- Pydantic 模型定義 ---


class FileUploadForm(BaseModel):
    """檔案上傳表單模型"""

    file: FileStorage = Field(..., description="要上傳的檔案")


class FileUploadResponse(BaseModel):
    """檔案上傳成功的回應模型"""

    id: int
    filename: str
    size_bytes: int
    message: str = "File uploaded successfully"


class FileInfo(BaseModel):
    """單一檔案的資訊模型"""

    id: int
    filename: str
    size_bytes: int
    upload_time: datetime
    del_time: datetime | None


class FileListResponse(BaseModel):
    """檔案列表的回應模型"""

    files: list[FileInfo]


# --- API 端點定義 ---


@filectrl.post(
    "/upload",
    summary="上傳單一檔案",
    responses={200: FileUploadResponse},
    security=[{"BearerAuth": []}],
)
@permission_required("file:upload")
def upload_single_file(form: FileUploadForm):
    """
    上傳一個檔案。
    - 需要 `file:upload` 權限。
    - 後端會檢查使用者的檔案數量配額。
    """
    # 從 JWT 取得當前使用者是誰
    current_user_account = get_jwt_identity()

    with get_db_session() as db:
        # 建立 Controller 實例並傳入需要的參數
        logic = UploadFile(
            session=db, user_account=current_user_account, file=form.file
        )
        # 呼叫核心邏輯並回傳結果
        return logic.save()


@filectrl.get(
    "/list",
    summary="獲取檔案列表",
    responses={200: FileListResponse},
    security=[{"BearerAuth": []}],
)
@permission_required("file:read:own")
def list_files():
    """
    獲取當前使用者的檔案列表。
    - 需要 `file:read` 權限。
    """
    current_user_account = get_jwt_identity()
    with get_db_session() as db:
        from share.model.model import User, File

        user = db.query(User).filter(User.account == current_user_account).one_or_none()
        if not user:
            return {"files": []}

        files = db.query(File).filter(File.owner_id == user.id).all()

        file_list = [
            FileInfo(
                id=f.id,
                filename=f.filename,
                size_bytes=f.file_size,
                upload_time=f.createTime,
                del_time=f.expiry_time,
            )
            for f in files
        ]
        return FileListResponse(files=file_list).model_dump()
