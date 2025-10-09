from flask_openapi3 import APIBlueprint, Tag
from flask import send_file, abort, request
from flask_openapi3.models.file import FileStorage
from pydantic import BaseModel, Field
from flask_jwt_extended import get_jwt_identity, create_access_token, decode_token
from jwt.exceptions import PyJWTError
from datetime import datetime, timedelta

from schema.request_userCtrl import FileInfo  # 新增匯入

from util.db import get_db_session
from util.auth import permission_required
from controller.Cont_fileCtrl import (
    UploadFile,
    DownloadFile,
    DeleteFile,
    ListFiles,
    UpdateFileStatus,
    CreateShareLink,
    RemoveShareLink,
)

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


class UpdateFileStatusForm(BaseModel):
    """更新檔案狀態的請求模型"""

    is_permanent: bool = Field(..., description="是否設定為永久檔案")


class FileIdPath(BaseModel):
    """檔案路徑參數模型"""

    safe_filename: str = Field(..., description="檔案安全名稱")


class ShareTokenPath(BaseModel):
    """分享 Token 的路徑參數模型"""

    share_token: str = Field(..., description="檔案分享 token")


class ShareLinkResponse(BaseModel):
    """建立分享連結的回應模型"""

    share_token: str


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
    current_user_account = get_jwt_identity()
    with get_db_session() as db:
        logic = UploadFile(
            session=db, user_account=current_user_account, file=form.file
        )
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
        logic = ListFiles(
            session=db,
            user_account=current_user_account,
            filename=query.filename,
            sort_by=query.sort_by,
            order=query.order,
        )
        result = logic.run()

        # 將 File ORM 物件轉換為 FileInfo Pydantic 模型
        file_list_pydantic = [
            FileInfo(
                id=f.id,
                filename=f.filename,
                size_bytes=f.file_size,
                upload_time=f.createTime,
                del_time=f.expiry_time,
                is_permanent=f.is_permanent,
                safe_filename=f.safe_filename,
                share_token=f.share_token,
                download_url=f.download_url,
            )
            for f in result["files"]
        ]

        return FileListResponse(
            files=file_list_pydantic,
            stats=result["stats"],
            limits=result["limits"],
        ).model_dump()


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
            share_token=updated_file.share_token,
        ).model_dump()


@filectrl.post(
    "/<string:safe_filename>/download-token",
    summary="為下載檔案建立一個一次性的 token",
    responses={200: {"description": "Token created successfully"}},
    security=[{"BearerAuth": []}],
)
@permission_required("file:upload")
def create_download_token(path: FileIdPath):
    """
    為下載檔案建立一個短時間有效的一次性 token。
    - 需要 `file:upload` 權限。
    - Token 內會包含檔案資訊，並在 5 分鐘後過期。
    """
    current_user_account = get_jwt_identity()

    # 驗證使用者是否有權限存取此檔案
    with get_db_session() as db:
        logic = DownloadFile(
            session=db,
            user_account=current_user_account,
            safe_filename=path.safe_filename,
        )
        # 執行 run() 來觸發權限檢查，若無權限會拋出例外
        logic.run()

    # 建立一個包含特定下載聲明 (claim) 且短時間有效的 JWT
    additional_claims = {"download_file": path.safe_filename}
    download_token = create_access_token(
        identity=current_user_account,
        expires_delta=timedelta(minutes=5),
        additional_claims=additional_claims,
    )
    return {"download_token": download_token}


@filectrl.get(
    "/<string:safe_filename>/download",
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
            safe_filename=path.safe_filename,
        )
        file_info = logic.run()
        return send_file(
            file_info["storage_path"],
            as_attachment=True,
            download_name=file_info["filename"],
        )


@filectrl.delete(
    "/<string:safe_filename>",
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
            safe_filename=path.safe_filename,
        )
        return logic.run()


@filectrl.post(
    "/<string:safe_filename>/share",
    summary="建立檔案的分享連結",
    responses={200: ShareLinkResponse},
    security=[{"BearerAuth": []}],
)
@permission_required("file:share")
def create_share_link(path: FileIdPath):
    """
    為指定的檔案建立一個公開的分享連結。
    - 如果連結已存在，則直接回傳現有的。
    - 需要 `file:share` 權限。
    """
    current_user_account = get_jwt_identity()
    with get_db_session() as db:
        logic = CreateShareLink(
            session=db,
            user_account=current_user_account,
            safe_filename=path.safe_filename,
        )
        file_record = logic.run()
        return {"share_token": file_record.share_token}


@filectrl.delete(
    "/<string:safe_filename>/share",
    summary="移除檔案的分享連結",
    responses={200: {"description": "Share link removed successfully"}},
    security=[{"BearerAuth": []}],
)
@permission_required("file:share")
def remove_share_link(path: FileIdPath):
    """
    移除指定檔案的公開分享連結。
    - 需要 `file:share` 權限。
    """
    current_user_account = get_jwt_identity()
    with get_db_session() as db:
        logic = RemoveShareLink(
            session=db,
            user_account=current_user_account,
            safe_filename=path.safe_filename,
        )
        return logic.run()


@filectrl.get(
    "/shared/<string:share_token>",
    summary="透過分享連結下載檔案",
    # 此處故意不放 security 參數，使其成為公開 API
)
def public_download_file(path: ShareTokenPath):
    """
    處理公開分享連結的下載請求。
    - 此 API 無須 JWT 認證。
    """
    with get_db_session() as db:
        from share.model.model import File
        import os

        file_record = (
            db.query(File).filter(File.share_token == path.share_token).one_or_none()
        )

        if not file_record or not os.path.exists(file_record.storage_path):
            abort(404, "File not found or link has expired.")

        return send_file(
            file_record.storage_path,
            as_attachment=True,
            download_name=file_record.filename,
        )


@filectrl.get(
    "/download_with_token",
    summary="使用一次性 token 下載檔案",
    # 此端點為公開，由 token 內容進行驗證
)
def download_with_token():
    """
    使用短時間有效的一次性 token 來下載檔案。
    - Token 從 URL 查詢參數中獲取。
    - Token 必須是有效的，且包含 'download_file' 的聲明。
    """
    token = request.args.get("token")
    if not token:
        abort(401, "Missing download token.")

    try:
        # 解碼 JWT，這會自動檢查過期時間
        decoded_token = decode_token(token)

        # 從 token 中獲取使用者身份和檔案名稱
        user_account = decoded_token["sub"]
        safe_filename = decoded_token.get("download_file")

        if not safe_filename:
            abort(400, "Invalid token: missing 'download_file' claim.")

        # 使用從 token 獲取的資訊來下載檔案
        with get_db_session() as db:
            logic = DownloadFile(
                session=db,
                user_account=user_account,
                safe_filename=safe_filename,
            )
            file_info = logic.run()
            return send_file(
                file_info["storage_path"],
                as_attachment=True,
                download_name=file_info["filename"],
            )

    except PyJWTError as e:
        # 捕獲所有 JWT 相關的錯誤 (例如過期、簽名無效)
        abort(401, f"Invalid or expired token: {e}")
