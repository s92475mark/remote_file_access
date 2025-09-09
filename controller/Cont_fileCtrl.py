import os
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from flask import abort
from werkzeug.datastructures import FileStorage

from share.model.model import User, File
from util.global_variable import global_variable


class UploadFile:
    """處理檔案上傳的核心邏輯"""

    def __init__(self, session: Session, user_account: str, file: FileStorage):
        self.session = session
        self.user_account = user_account
        self.file = file

    def save(self):
        # 1. 查詢使用者和他的角色/檔案資訊
        user = (
            self.session.query(User)
            .filter(User.account == self.user_account)
            .one_or_none()
        )
        if not user:
            abort(404, "User not found.")

        # 2. 決定使用者的配額 (取使用者所有角色中最高的配額)
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
        safe_filename = f"{uuid.uuid4().hex}{extension}"
        # 組合儲存路徑 (使用者的專屬資料夾)
        save_path = os.path.join(user.storage_path, safe_filename)

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
        self, session: Session, user_account: str, file_id: int, is_permanent: bool
    ):
        self.session = session
        self.user_account = user_account
        self.file_id = file_id
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
            self.session.query(File).filter(File.id == self.file_id).one_or_none()
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
