"""Seed para entornos dev/demo. Crea un admin si no existe.

Uso:
    python -m services.api.app.infrastructure.seed
"""

from services.shared.logging_setup import get_logger, setup_logging
from services.shared.models.base import session_scope
from services.shared.models.enums import UserRole
from services.shared.models.user import User
from services.shared.security import hash_password


def seed() -> None:
    setup_logging(service_name="seed")
    logger = get_logger()

    with session_scope() as db:
        if db.query(User).filter(User.email == "admin@mediaintel.local").first():
            logger.info("seed_skipped_admin_exists")
            return
        admin = User(
            email="admin@mediaintel.local",
            password_hash=hash_password("ChangeMe123!"),
            full_name="Admin demo",
            role=UserRole.ADMIN.value,
            is_active=True,
        )
        analyst = User(
            email="analyst@mediaintel.local",
            password_hash=hash_password("ChangeMe123!"),
            full_name="Analista demo",
            role=UserRole.ANALYST.value,
            is_active=True,
        )
        db.add_all([admin, analyst])
        logger.info("seed_users_created")


if __name__ == "__main__":
    seed()
