import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User, UserStatus, UserRole, LoginProvider
from app.core.security import PasswordManager


def get_unique_id():
    """Get unique identifier for test data."""
    return str(uuid.uuid4())[:8]


class TestUserModel:
    """Test User model functionality."""

    @pytest.mark.asyncio
    async def test_user_creation(self, test_db: AsyncSession):
        """Test creating a new user with minimal required fields."""
        unique_id = get_unique_id()

        user = User(
            email=f"test_{unique_id}@example.com",
            username=f"testuser_{unique_id}",
            password_hash=PasswordManager.hash_password("password123"),
        )

        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        assert user.id is not None
        assert user.email == f"test_{unique_id}@example.com"
        assert user.username == f"testuser_{unique_id}"
        assert user.password_hash is not None
        assert user.created_at is not None
        assert user.updated_at is not None

    @pytest.mark.asyncio
    async def test_user_default_values(self, test_db: AsyncSession):
        """Test that default values are set correctly."""
        unique_id = get_unique_id()

        user = User(
            email=f"defaults_{unique_id}@example.com",
            username=f"defaultuser_{unique_id}",
            password_hash=PasswordManager.hash_password("password123"),
        )

        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        assert user.status == UserStatus.ACTIVE
        assert user.role == UserRole.USER
        assert user.login_provider == LoginProvider.LOCAL
        assert user.is_verified is False
        assert user.is_superuser is False
        assert user.mfa_enabled is False
        assert user.failed_login_attempts == 0
        assert user.is_locked is False
        assert user.login_count == 0

    @pytest.mark.asyncio
    async def test_user_password_hashing(self, test_db: AsyncSession):
        """Test that password is properly hashed."""
        unique_id = get_unique_id()
        original_password = "my_secret_password"
        hashed = PasswordManager.hash_password(original_password)

        user = User(
            email=f"hashing_{unique_id}@example.com",
            username=f"hashuser_{unique_id}",
            password_hash=hashed,
        )

        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        assert user.password_hash != original_password
        assert user.password_hash.startswith("$2b$")
        assert PasswordManager.verify_password(original_password, user.password_hash)

    @pytest.mark.asyncio
    async def test_user_full_name_property(self, test_db: AsyncSession):
        """Test full_name property calculation."""
        user1 = User(
            email="test1@example.com",
            username="testuser1",
            first_name="John",
            last_name="Doe",
            password_hash="hashed",
        )
        assert user1.full_name == "John Doe"

        user2 = User(
            email="test2@example.com",
            username="testuser2",
            first_name="John",
            password_hash="hashed",
        )
        assert user2.full_name == "John"

        user3 = User(
            email="test3@example.com", username="testuser3", password_hash="hashed"
        )
        assert user3.full_name is None

    @pytest.mark.asyncio
    async def test_user_is_active_property(self, test_db: AsyncSession):
        """Test is_active property based on status."""
        user1 = User(
            email="active@example.com",
            username="activeuser",
            status=UserStatus.ACTIVE,
            password_hash="hashed",
        )
        assert user1.is_active is True

        user2 = User(
            email="inactive@example.com",
            username="inactiveuser",
            status=UserStatus.INACTIVE,
            password_hash="hashed",
        )
        assert user2.is_active is False

    @pytest.mark.asyncio
    async def test_user_public_name_property(self, test_db: AsyncSession):
        """Test public_name property fallback logic."""
        user1 = User(
            email="test1@example.com",
            username="testuser1",
            display_name="John Smithy",
            first_name="John",
            last_name="Smithy",
            password_hash="hashed",
        )
        assert user1.public_name == "John Smithy"

        user2 = User(
            email="test2@example.com",
            username="testuser2",
            first_name="John",
            last_name="Doe",
            password_hash="hashed",
        )
        assert user2.public_name == "John Doe"

        user3 = User(
            email="test3@example.com", username="c00luser", password_hash="hashed"
        )
        assert user3.public_name == "c00luser"

    @pytest.mark.asyncio
    async def test_user_email_unique_constraint(self, test_db: AsyncSession):
        """Test that email must be unique."""
        unique_id = get_unique_id()

        user1 = User(
            email=f"unique_{unique_id}@example.com",
            username=f"uniqueuser1_{unique_id}",
            password_hash="hashed",
        )

        user2 = User(
            email=f"unique_{unique_id}@example.com",  # Same email!
            username=f"uniqueuser2_{unique_id}",
            password_hash="hashed",
        )

        test_db.add(user1)
        await test_db.commit()

        test_db.add(user2)

        with pytest.raises(Exception):
            await test_db.commit()

    @pytest.mark.asyncio
    async def test_user_username_unique_constraint(self, test_db: AsyncSession):
        """Test that username must be unique."""
        unique_id = get_unique_id()

        user1 = User(
            email=f"username1_{unique_id}@example.com",
            username=f"unique_testuser_{unique_id}",
            password_hash="hashed",
        )

        user2 = User(
            email=f"username2_{unique_id}@example.com",
            username=f"unique_testuser_{unique_id}",
            password_hash="hashed",
        )

        test_db.add(user1)
        await test_db.commit()

        test_db.add(user2)

        with pytest.raises(Exception):
            await test_db.commit()

    @pytest.mark.asyncio
    async def test_user_query_by_email(self, test_db: AsyncSession):
        """Test querying user by email."""
        unique_id = get_unique_id()

        user = User(
            email=f"findgf_{unique_id}@example.com",
            username=f"finduser_{unique_id}",
            first_name="Find",
            last_name="Gf",  # impossible irl
            password_hash="hashed",
        )

        test_db.add(user)
        await test_db.commit()

        result = await test_db.execute(
            select(User).where(User.email == f"findgf_{unique_id}@example.com")
        )
        found_user = result.scalar_one_or_none()

        assert found_user is not None
        assert found_user.email == f"findgf_{unique_id}@example.com"
        assert found_user.username == f"finduser_{unique_id}"
        assert found_user.full_name == "Find Gf"

    @pytest.mark.asyncio
    async def test_user_enum_fields(self, test_db: AsyncSession):
        """Test enum fields work correctly."""
        unique_id = get_unique_id()

        user = User(
            email=f"enums_{unique_id}@example.com",
            username=f"enumuser_{unique_id}",
            status=UserStatus.ACTIVE,
            role=UserRole.ADMIN,
            login_provider=LoginProvider.LOCAL,
            password_hash="hashed",
        )

        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        assert user.status == UserStatus.ACTIVE
        assert user.role == UserRole.ADMIN
        assert (
            str(user.login_provider) == "local"
            or user.login_provider == LoginProvider.LOCAL
        )
        assert isinstance(user.status, UserStatus)
        assert isinstance(user.role, UserRole)

    @pytest.mark.asyncio
    async def test_user_repr(self, test_db: AsyncSession):
        """Test user string representation."""
        unique_id = get_unique_id()

        user = User(
            email=f"repr_{unique_id}@example.com",
            username=f"repruser_{unique_id}",
            status=UserStatus.ACTIVE,
            role=UserRole.USER,
            password_hash="hashed",
        )

        expected = f"<User(email=repr_{unique_id}@example.com, status=UserStatus.ACTIVE, role=UserRole.USER)>"
        assert repr(user) == expected
