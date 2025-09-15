import os
from datetime import datetime
from util.global_variable import global_variable
from share.model.model import File

class DeleteExpiredFilesJob:
    """
    刪除所有過期檔案的排程任務。
    """
    def run(self):
        print(f"[{datetime.now()}] Running job: DeleteExpiredFilesJob...")
        # 從全域變數中取得資料庫 session 工廠
        # 假設主要資料庫的鍵為 'default'
        SessionLocal = global_variable.database.get("default")
        if not SessionLocal:
            print("Error: Database session factory 'default' not found.")
            return

        session = SessionLocal()
        try:
            now = datetime.now()
            # 查詢所有 is_permanent 為 False 且 expiry_time 已過期的檔案
            expired_files = (
                session.query(File)
                .filter(File.is_permanent == False, File.expiry_time < now)
                .all()
            )

            if not expired_files:
                print("No expired files found.")
                return

            print(f"Found {len(expired_files)} expired files to delete.")

            for file_record in expired_files:
                try:
                    print(f"  - Deleting file: {file_record.filename} (ID: {file_record.id}, Path: {file_record.storage_path})")
                    # 1. 刪除實體檔案
                    if os.path.exists(file_record.storage_path):
                        os.remove(file_record.storage_path)
                        print(f"    - Physical file deleted successfully.")
                    else:
                        print(f"    - Warning: Physical file not found at {file_record.storage_path}.")

                    # 2. 從資料庫刪除紀錄
                    session.delete(file_record)
                    print(f"    - Database record marked for deletion.")
                except Exception as e:
                    print(f"    - Error deleting file {file_record.id}: {e}")
            
            # 3. 提交所有變更
            session.commit()
            print("Database changes committed.")

        except Exception as e:
            print(f"An error occurred during the job execution: {e}")
            session.rollback()
        finally:
            session.close()
            print("Job finished.")