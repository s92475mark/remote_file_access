from enum import Enum


class DocEnum(Enum):
    """
    可以給予 Enum 每個 member 一個自訂的 doc 字串 (可看作註解)。

    doc 放在 `=` 右邊的第二個參數中 (tuple 的 [1])。

    從每個 member 的 `__doc__` 取得 doc 字串。

    例如:
    ```python
    class MyEnum(DocEnum):
        A = "A", "Doc A"

    print(MyEnum.A.__doc__)
    # output: Doc A
    ```
    """

    def __new__(cls, value, doc=""):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.__doc__ = doc
        return obj


class RoleName(DocEnum):
    """角色名稱"""

    superadmin = "supperAdmin", "最高管理員"
    admin = "Admin", "管理員"
    lv1 = "lv1User", "一階使用者"
    lv2 = "lv2User", "二階使用者"
    lv3 = "lv3User", "三階使用者"


class RoleList(DocEnum):
    """for 下拉選單(不提供superadmin)所以獨立出來"""

    admin = "Admin", "管理員"
    lv1 = "lv1User", "一階使用者"
    lv2 = "lv2User", "二階使用者"
    lv3 = "lv3User", "三階使用者"


class permanent_file(DocEnum):
    """是否為永久檔案"""

    is_permanent = True, "永久檔案"
    not_permanent = False, "期限檔案"


class permission(DocEnum):
    """權限列表"""

    create_user = "user:create", "建新使用者"
    user_list = "user:read:list", "取得使用者列表"
    user_details = "user:read:details", "取得使用者詳情"
    user_update = "user:update", "修改使用者資料"
    user_assign_roles = "user:assign_roles", "指派使用者角色"
    user_delets = "user:delete", "刪除使用者"
    role_create = "role:create", "新增角色"
    role_read = "role:read", "查詢角色"
    role_update = "role:update", "修改角色權限"
    role_delete = "role:delete", "刪除角色"
    file_upload = "file:upload", "上傳檔案"
    file_read = "file:read:own", "讀取自己的檔案"
    file_delete = "file:delete:own", "刪除自己的檔案"
    file_share = "file:share", "建立分享連結"
    file_permanent = "file:set_permanent", "設定檔案為永久"
    file_manage_all = "file:manage:all", "管理所有檔案"
    audit_read = "audit:read", "讀取操作日誌"
