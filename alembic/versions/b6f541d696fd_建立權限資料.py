"""建立權限資料

Revision ID: b6f541d696fd
Revises: 14def0bbc48a
Create Date: 2025-08-25 16:18:30.340061

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'b6f541d696fd'
down_revision = None
branch_labels = None
depends_on = None


# 定義我們要新增的權限列表
permissions_to_create = [
    # User Management
    {'code': 'user:create', 'name': '新增使用者', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'user:read:list', 'name': '查詢使用者列表', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'user:read:details', 'name': '查詢使用者詳情', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'user:update', 'name': '修改使用者資料', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'user:assign_roles', 'name': '指派使用者角色', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'user:delete', 'name': '刪除使用者', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    # Role Management
    {'code': 'role:create', 'name': '新增角色', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'role:read', 'name': '查詢角色', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'role:update', 'name': '修改角色權限', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'role:delete', 'name': '刪除角色', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    # File Management (Basic)
    {'code': 'file:upload', 'name': '上傳檔案', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'file:read:own', 'name': '讀取自己的檔案', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'file:delete:own', 'name': '刪除自己的檔案', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'file:share', 'name': '建立分享連結', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    {'code': 'file:set_permanent', 'name': '設定檔案為永久', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    # File Management (Admin)
    {'code': 'file:manage:all', 'name': '管理所有檔案', 'createTime': datetime.now(), 'updateTime': datetime.now()},
    # System Management
    {'code': 'audit:read', 'name': '讀取操作日誌', 'createTime': datetime.now(), 'updateTime': datetime.now()},
]

def upgrade() -> None:
    # 獲取當前的資料庫連線
    conn = op.get_bind()

    # 定義 permissions, roles, 和 role_permissions 的表結構以供查詢和插入
    permissions_table = sa.table('permissions',
        sa.column('id', sa.Integer),
        sa.column('code', sa.String),
        sa.column('name', sa.String),
        sa.column('createTime', sa.DateTime),
        sa.column('updateTime', sa.DateTime)
    )
    roles_table = sa.table('roles',
        sa.column('id', sa.Integer),
        sa.column('role_name', sa.String)
    )
    role_permissions_table = sa.table('role_permissions',
        sa.column('role_id', sa.Integer),
        sa.column('permission_id', sa.Integer)
    )

    # 1. 批次插入所有新的權限
    op.bulk_insert(permissions_table, permissions_to_create)

    # 2. 查詢 'Super Admin' 角色的 ID
    super_admin_role_result = conn.execute(
        sa.select(roles_table.c.id).where(roles_table.c.role_name == 'Super Admin')
    ).scalar_one_or_none()

    # 如果 Super Admin 角色存在，才進行後續操作
    if super_admin_role_result is not None:
        # 3. 查詢所有權限的 ID
        all_permissions = conn.execute(sa.select(permissions_table.c.id)).fetchall()
        permission_ids = [p[0] for p in all_permissions]

        # 4. 準備要插入到關聯表的資料
        associations_to_create = []
        for perm_id in permission_ids:
            associations_to_create.append({
                'role_id': super_admin_role_result,
                'permission_id': perm_id
            })
        
        # 5. 將所有權限與 Super Admin 角色進行關聯
        if associations_to_create:
            op.bulk_insert(role_permissions_table, associations_to_create)


def downgrade() -> None:
    # 在降級時，我們需要刪除這些權限以及它們的關聯
    permission_codes = [p['code'] for p in permissions_to_create]
    # 使用 text() 來處理 IN 子句，這是 SQLAlchemy 核心的推薦作法
    op.execute(
        sa.text("DELETE FROM permissions WHERE code IN :codes").bindparams(
            sa.bindparam('codes', expanding=True)
        )
    )
    # 關聯表中的紀錄會因為資料庫的 ondelete="CASCADE" 設定而被自動刪除