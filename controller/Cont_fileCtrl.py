import os
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from flask import abort
from werkzeug.datastructures import FileStorage

from share.model.model import User, File, Role
from util.global_variable import global_variable
from sqlalchemy import label, select, func
from flask_jwt_extended import get_jwt_identity, create_access_token, decode_token


class UploadFile:
    """處理檔案上傳的核心邏輯"""

    def __init__(self, session: Session, user_account: str, file: FileStorage):
        self.session = session
        self.user_account = user_account
        self.file = file

    def save(self):
        user = (
            self.session.query(User)
            .filter(User.account == self.user_account)
            .one_or_none()
        )
        if not user:
            abort(404, "User not found.")
        file_limit = -1
        lifetime_days = -1
        if user.roles:
            # 過濾掉無限配額(-1)，然後取最大值。如果過濾後列表為空(代表所有角色都是無限)，則維持-1。
            limits = [r.file_limit for r in user.roles if r.file_limit != -1]
            file_limit = max(limits) if limits else -1

            lifetimes = [
                r.file_lifetime_days for r in user.roles if r.file_lifetime_days != -1
            ]
            lifetime_days = max(lifetimes) if lifetimes else -1

        # 3. 檢查檔案數量配額
        if file_limit != -1:
            # len(user.files) 會觸發一次查詢，來計算目前檔案數量
            if len(user.files) >= file_limit:
                abort(
                    403,
                    f"File upload limit exceeded. Your limit is {file_limit} files.",
                )

        # 4. 處理檔案儲存
        # 取得副檔名
        _, extension = os.path.splitext(self.file.filename)
        # 產生一個安全、唯一的檔名
        safe_filename = uuid.uuid4().hex
        safe_filename_extension = f"{safe_filename}{extension}"

        # 組合儲存路徑 (使用者的專屬資料夾)
        save_path = os.path.join(user.storage_path, safe_filename_extension)

        # 儲存檔案到磁碟
        self.file.save(save_path)
        file_size = os.path.getsize(save_path)

        # 5. 計算過期時間
        is_permanent = False
        if lifetime_days != -1:
            # 如果角色有設定天數，就使用該天數
            expiry_time = datetime.now() + timedelta(days=lifetime_days)
        else:
            # 如果角色設定為永久 (-1)，則提供一個預設天數 (例如 7 天)
            default_days = 7
            expiry_time = datetime.now() + timedelta(days=default_days)

        # 6. 建立檔案的資料庫紀錄
        new_file_record = File(
            filename=self.file.filename,
            safe_filename=safe_filename,
            storage_path=save_path,
            file_size=file_size,
            owner_id=user.id,
            expiry_time=expiry_time,
            is_permanent=is_permanent,
        )
        self.session.add(new_file_record)
        self.session.commit()
        self.session.refresh(new_file_record)

        # 7. 回傳成功訊息
        return {
            "id": new_file_record.id,
            "filename": new_file_record.filename,
            "size_bytes": new_file_record.file_size,
            "message": "File uploaded successfully",
        }


class UpdateFileStatus:
    """處理檔案狀態切換的核心邏輯"""

    def __init__(
        self,
        session: Session,
        user_account: str,
        safe_filename: int,
        is_permanent: bool,
    ):
        self.session = session
        self.user_account = user_account
        self.safe_filename = safe_filename
        self.is_permanent = is_permanent

    def run(self):
        # 1. 查詢使用者和檔案
        user = (
            self.session.query(User)
            .filter(User.account == self.user_account)
            .one_or_none()
        )
        if not user:
            abort(404, "User not found.")

        file_to_update = (
            self.session.query(File)
            .filter(File.safe_filename == self.safe_filename)
            .one_or_none()
        )
        if not file_to_update:
            abort(404, "File not found.")

        # 2. 檢查檔案所有權
        if file_to_update.owner_id != user.id:
            abort(403, "You do not have permission to modify this file.")

        # 3. 根據請求的狀態執行操作
        if self.is_permanent:
            # --- 切換為永久 ---
            # a. 檢查配額
            perm_limits = [
                r.permanent_file_limit
                for r in user.roles
                if r.permanent_file_limit != -1
            ]
            permanent_file_limit = max(perm_limits) if perm_limits else -1

            if permanent_file_limit != -1:
                current_permanent_files = (
                    self.session.query(File)
                    .filter(File.owner_id == user.id, File.is_permanent == True)
                    .count()
                )
                if current_permanent_files >= permanent_file_limit:
                    abort(
                        403,
                        f"Permanent file quota exceeded. Your limit is {permanent_file_limit} files.",
                    )

            # b. 更新狀態
            file_to_update.is_permanent = True

        else:
            # --- 切換為非永久 ---
            # 根據新的邏輯，只需更新 is_permanent 旗標。
            # expiry_time 維持上傳時計算出的原始值。
            file_to_update.is_permanent = False

        self.session.commit()
        self.session.refresh(file_to_update)

        return file_to_update


class DownloadFile:
    """處理檔案下載的核心邏輯"""

    def __init__(self, session: Session, user_account: str, safe_filename: str):
        self.session = session
        self.user_account = user_account
        self.safe_filename = safe_filename

    def run(self):
        # 1. 查詢使用者和檔案
        user = (
            self.session.query(User)
            .filter(User.account == self.user_account)
            .one_or_none()
        )
        if not user:
            abort(404, "User not found.")

        file_to_download = (
            self.session.query(File)
            .filter(File.safe_filename == self.safe_filename)
            .one_or_none()
        )

        if not file_to_download:
            abort(404, "File not found.")

        # 2. 檢查檔案所有權
        if file_to_download.owner_id != user.id:
            abort(403, "You do not have permission to download this file.")

        # 3. 檢查實體檔案是否存在
        if not os.path.exists(file_to_download.storage_path):
            abort(404, "File not found on server storage.")

        # 4. 回傳給 View 層需要的資訊
        return {
            "storage_path": file_to_download.storage_path,
            "filename": file_to_download.filename,
        }


class DeleteFile:
    """處理檔案刪除的核心邏輯"""

    def __init__(self, session: Session, user_account: str, safe_filename: str):
        self.session = session
        self.user_account = user_account
        self.save_filename = safe_filename

    def run(self):
        # 1. 查詢使用者和檔案
        user = (
            self.session.query(User)
            .filter(User.account == self.user_account)
            .one_or_none()
        )
        if not user:
            abort(404, "User not found.")

        file_to_delete = (
            self.session.query(File)
            .filter(File.safe_filename == self.save_filename)
            .one_or_none()
        )
        if not file_to_delete:
            abort(404, "File not found.")

        # 2. 檢查檔案所有權
        if file_to_delete.owner_id != user.id:
            abort(403, "You do not have permission to delete this file.")

        # 3. 檢查實體檔案是否存在並刪除
        if os.path.exists(file_to_delete.storage_path):
            os.remove(file_to_delete.storage_path)
        else:
            # 如果檔案不存在於磁碟，但資料庫有紀錄，也視為成功，只刪除資料庫紀錄
            print(
                f"Warning: File {file_to_delete.storage_path} not found on disk but exists in DB. Deleting DB record."
            )

        # 4. 從資料庫刪除紀錄
        self.session.delete(file_to_delete)
        self.session.commit()

        return {"message": "File deleted successfully"}


class ListFiles:
    """處理獲取檔案列表的核心邏輯"""

    def __init__(
        self,
        session: Session,
        user_account: str,
        filename: str = None,
        sort_by: str = "upload_time",
        order: str = "desc",
    ):
        self.session = session
        self.user_account = user_account
        self.filename = filename
        self.sort_by = sort_by
        self.order = order

    def run(self):
        from sqlalchemy import case, cast, String, func

        download_token = create_access_token(
            identity=self.user_account,
            expires_delta=timedelta(minutes=5),
        )
        download_token_str = (
            f"/api/files/download_with_token?token={download_token}&filename="
        )

        # 查詢 1: 獲取使用者及其權限限制
        user_and_limits = (
            self.session.query(
                User.id.label("user_id"),
                Role.file_limit,
                Role.permanent_file_limit,
            )
            .join(User.roles)
            .filter(User.account == self.user_account)
            .order_by(Role.level.asc())
            .limit(1)
            .one_or_none()
        )

        if not user_and_limits:
            return {
                "files": [],
                "stats": {"file_count": 0, "permanent_file_count": 0},
                "limits": {"file_limit": 0, "permanent_file_limit": 0},
            }

        # 查詢 2: 獲取檔案統計數據
        file_stats = (
            self.session.query(
                func.count(File.id).label("file_count"),
                func.sum(case((File.is_permanent == True, 1), else_=0)).label(
                    "permanent_file_count"
                ),
            )
            .filter(File.owner_id == user_and_limits.user_id)
            .first()
        )

        # 查詢 3: 獲取檔案列表本身

        q = select(
            File.id.label("id"),
            File.filename.label("filename"),
            File.file_size.label("file_seize"),
            File.createTime.label("createTime"),
            File.expiry_time.label("expiry_time"),
            File.is_permanent.label("is_permanent"),
            File.safe_filename.label("safe_filename"),
            File.share_token.label("share_token"),
            File.file_size.label("file_size"),
            (download_token_str + File.filename).label("download_url"),
        ).where(File.owner_id == user_and_limits.user_id)
        sort_column_map = {
            "filename": File.filename,
            "size_bytes": File.file_size,
            "upload_time": File.createTime,
        }
        sort_column = sort_column_map.get(self.sort_by, File.createTime)

        if self.order == "asc":
            q = q.order_by(sort_column.asc())
        else:
            q = q.order_by(sort_column.desc())

        if self.filename:
            q = q.where(File.filename.like(f"%{self.filename}%"))

        files = self.session.execute(q).all()
        # 組合所有結果並回傳
        return {
            "files": files,
            "stats": {
                "file_count": file_stats.file_count if file_stats else 0,
                "permanent_file_count": file_stats.permanent_file_count
                if file_stats
                else 0,
            },
            "limits": {
                "file_limit": "∞"
                if user_and_limits.file_limit == -1
                else user_and_limits.file_limit,
                "permanent_file_limit": "∞"
                if user_and_limits.permanent_file_limit == -1
                else user_and_limits.permanent_file_limit,
            },
        }


class CreateShareLink:
    """建立分享連結的核心邏輯"""

    def __init__(self, session: Session, user_account: str, safe_filename: str):
        self.session = session
        self.user_account = user_account
        self.safe_filename = safe_filename

    def run(self):
        user = (
            self.session.query(User)
            .filter(User.account == self.user_account)
            .one_or_none()
        )
        if not user:
            abort(404, "User not found.")

        file_record = (
            self.session.query(File)
            .filter(File.safe_filename == self.safe_filename, File.owner_id == user.id)
            .one_or_none()
        )

        if not file_record:
            abort(404, "File not found or you do not have permission.")

        # 如果 token 已存在，直接回傳
        if file_record.share_token:
            return file_record

        # 產生新 token 並儲存
        file_record.share_token = uuid.uuid4().hex
        self.session.commit()
        self.session.refresh(file_record)

        return file_record


class RemoveShareLink:
    """移除分享連結的核心邏輯"""

    def __init__(self, session: Session, user_account: str, safe_filename: str):
        self.session = session
        self.user_account = user_account
        self.safe_filename = safe_filename

    def run(self):
        user = (
            self.session.query(User)
            .filter(User.account == self.user_account)
            .one_or_none()
        )
        if not user:
            abort(404, "User not found.")

        file_record = (
            self.session.query(File)
            .filter(File.safe_filename == self.safe_filename, File.owner_id == user.id)
            .one_or_none()
        )

        if not file_record:
            abort(404, "File not found or you do not have permission.")

        # 如果 token 本來就沒有，也直接回傳成功
        if not file_record.share_token:
            return {"message": "Share link already removed."}

        # 移除 token 並儲存
        file_record.share_token = None
        self.session.commit()

        return {"message": "Share link removed successfully."}
