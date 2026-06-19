import logging
from typing import Optional

from moso_core.identity.models import IdentityResult, IdentityLevel, PermissionFlags

logger = logging.getLogger(__name__)


class PermissionResolver:
    def __init__(self):
        self._sensitive_actions: set[str] = {
            "delete", "rm", "remove", "uninstall",
            "shutdown", "reboot", "format",
            "execute", "run", "shell",
            "admin", "sudo", "elevate",
            "password", "credential", "token",
            "share", "upload", "sync",
        }

    def resolve(self, result: IdentityResult, action: Optional[str] = None) -> bool:
        if result.level == IdentityLevel.OWNER:
            return True

        if result.level == IdentityLevel.LIKELY_OWNER:
            if action and self._is_sensitive(action):
                logger.info("Sensitive action '%s' requires confirmation (likely owner)", action)
                return False
            return True

        if result.level == IdentityLevel.GUEST:
            logger.info("Guest access: limited permissions")
            return False

        return False

    def resolve_permission_flags(self, result: IdentityResult) -> PermissionFlags:
        return result.permission

    def _is_sensitive(self, action: str) -> bool:
        action_lower = action.lower()
        for keyword in self._sensitive_actions:
            if keyword in action_lower:
                return True
        return False

    def add_sensitive_action(self, action: str) -> None:
        self._sensitive_actions.add(action.lower())

    def remove_sensitive_action(self, action: str) -> None:
        self._sensitive_actions.discard(action.lower())
