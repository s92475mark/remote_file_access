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


class permanent_file(DocEnum):
    """是否為永久檔案"""

    is_permanent = True, "永久檔案"
    not_permanent = False, "期限檔案"
