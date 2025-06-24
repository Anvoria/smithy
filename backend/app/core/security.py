import secrets
import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, Dict, Any

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import settings

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class PasswordManager:
    """Password hashing and verification utilities"""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.
        :param password: The plain text password to hash.
        :return: The hashed password.
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a plain text password against a hashed password.
        :param plain_password: The plain text password to verify.
        :param hashed_password: The hashed password to check against.
        :return: True if the password matches, False otherwise.
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def generate_random_password(length: int = 12) -> str:
        """
        Generate a random password with a mix of letters, digits, and special characters.
        :param length: The desired length of the password.
        :return: A randomly generated password string.
        """
        import string

        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    @staticmethod
    def validate_password_strength(password: str) -> bool:
        """
        Validate the strength of a password.
        :param password: The password string to validate.
        :return: True if the password meets strength requirements, False otherwise.
        """
        if len(password) < 8:
            return False
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        return all([has_upper, has_lower, has_digit, has_special])


class TokenManager:
    """JWT token management utilities using python-jose"""

    @staticmethod
    def create_access_token(
        subject: str,
        user_id: str,
        role: str,
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a JWT access token with custom claims.
        :param subject: User identifier (username or email).
        :param user_id: Unique user ID (UUID).
        :param role: User role (e.g., admin, user).
        :param expires_delta: Optional expiration time delta for the token.
        :param additional_claims: Optional additional claims to include in the token.
        :return:
        """
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
            )

        payload = {
            "sub": subject,
            "user_id": user_id,
            "role": role,
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "access",
            "jti": str(uuid.uuid4()),
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_refresh_token(
        subject: str, user_id: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token.
        :param subject: User identifier (username or email).
        :param user_id: Unique user ID (UUID).
        :param expires_delta: Optional expiration time delta for the token.
        :return:
        """
        if expires_delta:
            expire = datetime.now(UTC) + expires_delta
        else:
            expire = datetime.now(UTC) + timedelta(
                days=settings.REFRESH_TOKEN_EXPIRE_DAYS
            )

        payload = {
            "sub": subject,
            "user_id": user_id,
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "refresh",
            "jti": str(uuid.uuid4()),
        }

        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode a JWT token and verify its signature.
        :param token:
        :return: Decoded token payload as a dictionary.
        """
        try:
            return jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": True},
            )
        except JWTError as e:
            msg = str(e)
            if "Signature has expired" in msg:
                raise ValueError("Token has expired")
            raise ValueError(f"Invalid token: {msg}")

    @staticmethod
    def get_token_jti(token: str) -> Optional[str]:
        """
        Extract the JWT ID (JTI) from a JWT token without verifying its signature.
        :param token: The JWT token string to decode.
        :return: The JTI (JWT ID) if present, None if the token is invalid or does not contain a JTI.
        """
        try:
            # Decode without verification to get JTI
            payload = jwt.decode(
                token,
                "",  # No key because we are not verifying the signature
                options={"verify_signature": False, "verify_exp": False},
            )
            return payload.get("jti")
        except JWTError:
            return None


class VerificationTokenManager:
    """Utilities for email verification, MFA, and password reset tokens"""

    @staticmethod
    def generate_verification_token() -> str:
        """
        Generate secure email verification/partial authentication token
        :return: A secure token string for email verification or partial authentication.
        """
        return secrets.token_urlsafe(32)

    @staticmethod
    def generate_reset_token() -> str:
        """
        Generate secure password reset token
        :return: A secure token string for password reset.
        """
        return secrets.token_urlsafe(32)
