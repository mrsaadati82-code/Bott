# ============================================================
# core/permission_manager.py - Role & permission checks
# ============================================================

import json
from typing import List, Optional

from database.db import db
from config import SUPER_ADMIN_IDS


# Roles
ROLE_USER        = "user"
ROLE_ADMIN       = "admin"
ROLE_SUPER_ADMIN = "super_admin"
ROLE_RESELLER    = "reseller"


def is_super_admin(bale_user_id: int) -> bool:
    if int(bale_user_id) in SUPER_ADMIN_IDS:
        return True
    row = db.fetchone(
        """SELECT a.role FROM admins a
            JOIN users u ON u.id = a.user_id
            WHERE u.bale_user_id=? AND a.role=?""",
        (int(bale_user_id), ROLE_SUPER_ADMIN),
    )
    return bool(row)


def get_role(bale_user_id: int) -> str:
    if is_super_admin(bale_user_id):
        return ROLE_SUPER_ADMIN
    row = db.fetchone(
        """SELECT a.role FROM admins a
            JOIN users u ON u.id = a.user_id
            WHERE u.bale_user_id=?""",
        (int(bale_user_id),),
    )
    if row:
        return row["role"]
    return ROLE_USER


def get_permissions(bale_user_id: int) -> List[str]:
    row = db.fetchone(
        """SELECT a.permissions FROM admins a
            JOIN users u ON u.id = a.user_id
            WHERE u.bale_user_id=?""",
        (int(bale_user_id),),
    )
    if not row or not row["permissions"]:
        return []
    try:
        return json.loads(row["permissions"])
    except Exception:
        return []


def has_permission(bale_user_id: int, perm: str) -> bool:
    if is_super_admin(bale_user_id):
        return True
    return perm in get_permissions(bale_user_id)


def grant_admin(user_id: int, role: str = ROLE_ADMIN,
                permissions: Optional[List[str]] = None):
    """Promote a users.id to admin/reseller."""
    perms_json = json.dumps(permissions or [])
    existing = db.fetchone("SELECT id FROM admins WHERE user_id=?", (user_id,))
    if existing:
        db.execute(
            "UPDATE admins SET role=?, permissions=? WHERE user_id=?",
            (role, perms_json, user_id),
        )
    else:
        db.execute(
            "INSERT INTO admins (user_id, role, permissions) VALUES (?, ?, ?)",
            (user_id, role, perms_json),
        )


def revoke_admin(user_id: int):
    db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
