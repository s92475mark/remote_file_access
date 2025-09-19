from flask_openapi3 import APIBlueprint, Tag
from flask import send_file
from flask_openapi3.models.file import FileStorage
from numpy import save
from pydantic import BaseModel, Field
from flask_jwt_extended import get_jwt_identity

from util.db import get_db_session
from util.auth import permission_required
from controller.Cont_fileCtrl import UploadFile, DownloadFile, DeleteFile
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
    is_permanent: bool
    safe_filename: str


class FileListResponse(BaseModel):
    """檔案列表的回應模型"""

    files: list[FileInfo]


class UpdateFileStatusForm(BaseModel):
    """更新檔案狀態的請求模型"""

    is_permanent: bool = Field(..., description="是否設定為永久檔案")


class FileIdPath(BaseModel):
    """檔案路徑參數模型"""

    safe_filename: str = Field(..., description="檔案安全名稱")


class FileListQuery(BaseModel):
    """檔案列表的查詢參數模型"""

    filename: str | None = Field(None, description="用於搜尋的檔案名稱關鍵字")
    sort_by: str | None = Field("upload_time", description="排序欄位")
    order: str | None = Field("desc", description="排序順序 (asc/desc)")


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
def list_files(query: FileListQuery):
    """
    獲取當前使用者的檔案列表。
    - 可選擇性地提供檔名進行搜尋，以及指定排序方式。
    - 需要 `file:read` 權限。
    """
    current_user_account = get_jwt_identity()
    with get_db_session() as db:
        from controller.Cont_fileCtrl import ListFiles

        logic = ListFiles(
            session=db,
            user_account=current_user_account,
            filename=query.filename,
            sort_by=query.sort_by,
            order=query.order,
        )
        files = logic.run()

        file_list = [
            FileInfo(
                id=f.id,
                filename=f.filename,
                size_bytes=f.file_size,
                upload_time=f.createTime,
                del_time=f.expiry_time,
                is_permanent=f.is_permanent,
                safe_filename=f.safe_filename,
            )
            for f in files
        ]
        return FileListResponse(files=file_list).model_dump()


@filectrl.patch(
    "/<string:safe_filename>/status",
    summary="更新檔案的永久狀態",
    responses={200: FileInfo},
    security=[{"BearerAuth": []}],
)
@permission_required("file:upload")
def update_file_status(path: FileIdPath, body: UpdateFileStatusForm):
    """
    切換檔案的永久/非永久狀態。
    - 需要 `file:update:status` 權限。
    - 切換為永久時，會檢查使用者的永久檔案配額。
    """
    current_user_account = get_jwt_identity()
    with get_db_session() as db:
        from controller.Cont_fileCtrl import UpdateFileStatus

        logic = UpdateFileStatus(
            session=db,
            user_account=current_user_account,
            safe_filename=path.safe_filename,
            is_permanent=body.is_permanent,
        )
        updated_file = logic.run()

        return FileInfo(
            id=updated_file.id,
            filename=updated_file.filename,
            size_bytes=updated_file.file_size,
            upload_time=updated_file.createTime,
            del_time=updated_file.expiry_time,
            is_permanent=updated_file.is_permanent,
            safe_filename=updated_file.safe_filename,
        ).model_dump()


@filectrl.get(
    "/<string:save_filename>/download",
    summary="下載檔案",
    security=[{"BearerAuth": []}],
)
@permission_required("file:upload")
def download_file(path: FileIdPath):
    """
    下載指定的檔案。
    - 需要 `file:download:own` 權限。
    - 回傳檔案串流。
    """
    current_user_account = get_jwt_identity()
    with get_db_session() as db:
        logic = DownloadFile(
            session=db,
            user_account=current_user_account,
            save_filename=path.save_filename,
        )
        file_info = logic.run()

        return send_file(
            file_info["storage_path"],
            as_attachment=True,
            download_name=file_info["filename"],
        )


@filectrl.delete(
    "/<string:save_filename>",
    summary="刪除檔案",
    responses={200: {"description": "File deleted successfully"}},
    security=[{"BearerAuth": []}],
)
@permission_required("file:delete:own")
def delete_file(path: FileIdPath):
    """
    刪除指定的檔案。
    - 需要 `file:delete:own` 權限。
    """
    current_user_account = get_jwt_identity()
    with get_db_session() as db:
        logic = DeleteFile(
            session=db,
            user_account=current_user_account,
            save_filename=path.save_filename,
        )
        return logic.run()
