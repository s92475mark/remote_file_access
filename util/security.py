from passlib.context import CryptContext

# 建立一個 CryptContext，設定 bcrypt 為預設演算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """將明文密碼進行雜湊加密"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """驗證明文密碼和雜湊後的是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)
