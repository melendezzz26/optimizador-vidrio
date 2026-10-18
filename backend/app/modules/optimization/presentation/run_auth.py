"""Reuse RBAC unchanged, with DB dependencies ending BEFORE streaming starts.

Only dependency wiring differs from ordinary JSON routes. All authentication
and authorization decisions remain in the shared public RBAC functions.
"""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials
from app.modules.authentication.presentation.dependencies import (
    bearer_scheme, get_database_session, get_user_reader, get_permission_reader,
    get_current_user, require_permission,
)


def get_run_user_reader(db=Depends(get_database_session, scope="function")):
    return get_user_reader(db)


def get_run_permission_reader(db=Depends(get_database_session, scope="function")):
    return get_permission_reader(db)


def get_run_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
                 reader=Depends(get_run_user_reader)):
    return get_current_user(credentials=credentials, user_reader=reader)


def run_permission(code):
    guard = require_permission(code)
    def check(user=Depends(get_run_user), reader=Depends(get_run_permission_reader)):
        return guard(user=user, permission_reader=reader)
    check.permission = code
    return check
