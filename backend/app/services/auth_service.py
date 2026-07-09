import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication and user bootstrap logic."""

    def __init__(self, db: Session):
        self.repo = UserRepository(db)

    def authenticate(self, username: str, password: str) -> User | None:
        user = self.repo.get_by_username(username)
        if user is None or not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def get_by_username(self, username: str) -> User | None:
        return self.repo.get_by_username(username)

    def seed_admin(self) -> None:
        """Create the admin user from env credentials if it doesn't exist yet."""
        if not settings.ADMIN_USER or not settings.ADMIN_PASSWORD:
            logger.info("ADMIN_USER/ADMIN_PASSWORD not set — skipping admin seeding.")
            return

        existing = self.repo.get_by_username(settings.ADMIN_USER)
        if existing is not None:
            logger.info("Admin user %r already exists — skipping.", settings.ADMIN_USER)
            return

        self.repo.create(
            username=settings.ADMIN_USER,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            is_admin=True,
        )
        logger.info("Seeded admin user %r.", settings.ADMIN_USER)
