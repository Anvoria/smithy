import json
import logging
from typing import Optional, Any, Union
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)

SESSION_KEY_PREFIX = "session"  # Prefix for session keys in Redis
BLACKLISTED_TOKEN_PREFIX = "blacklisted_token"  # Prefix for blacklisted tokens in Redis


class RedisClient:
    """Async Redis client for caching and session management."""

    def __init__(self):
        self._redis: Optional[Redis] = None

    async def connect(self) -> None:
        """
        Connect to the Redis server.
        """
        try:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
            )
            await self._redis.ping()
            logger.info("Connected to Redis server")

        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis server: {e}")
            if settings.ENVIRONMENT != "production":
                logger.warning(
                    "Redis connection failed in non-production environment. "
                    "Ensure Redis is running or check the configuration."
                )
                self._redis = None
            else:
                raise

    async def disconnect(self) -> None:
        """
        Disconnect from the Redis server.
        """
        if self._redis:
            try:
                await self._redis.aclose()
                logger.info("Disconnected from Redis server")
            except redis.ConnectionError as e:
                logger.error(f"Error disconnecting from Redis: {e}")
            finally:
                self._redis = None

    async def set(
        self,
        key: str,
        value: Union[str, dict, list, int, float],
        expire: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """
        Set a value in Redis with an optional expiration time.
        :param key: The key under which to store the value.
        :param value: The value to store, can be a string, dict, list, int, or float.
        :param expire: Optional expiration time in seconds or a timedelta object.
        :return: True if the operation was successful, False otherwise.
        """
        if not self._redis:
            logger.error("Redis client is not connected")
            return False

        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            elif isinstance(value, (int, float)):
                value = str(value)

            result = await self._redis.set(key, value, ex=expire)
            return bool(result)
        except redis.RedisError as e:
            logger.error(f"Error setting key '{key}' in Redis: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from Redis by key.
        :param key: The key to retrieve the value for.
        :return: The value stored under the key, or None if not found.
        """
        if not self._redis:
            logger.error("Redis client is not connected")
            return None

        try:
            value = await self._redis.get(key)
            if value is None:
                return None

            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value  # Return as string if not JSON
        except redis.RedisError as e:
            logger.error(f"Error getting key '{key}' from Redis: {e}")
            return None

    async def delete(self, key: str) -> bool:
        """
        Delete a key from Redis.
        :param key: The key to delete.
        :return: True if the key was deleted, False if it did not exist or an error occurred.
        """
        if not self._redis:
            logger.error("Redis client is not connected")
            return False

        try:
            result = await self._redis.delete(key)
            return bool(result)
        except redis.RedisError as e:
            logger.error(f"Error deleting key '{key}' from Redis: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in Redis.
        :param key: The key to check.
        :return: True if the key exists, False otherwise.
        """
        if not self._redis:
            logger.error("Redis client is not connected")
            return False

        try:
            return bool(await self._redis.exists(key))
        except redis.RedisError as e:
            logger.error(f"Error checking existence of key '{key}' in Redis: {e}")
            return False

    async def set_session(
        self,
        session_id: str,
        data: Union[str, dict, list, int, float],
        expire: Optional[Union[int, timedelta]] = None,
    ) -> bool:
        """
        Set a session in Redis with an optional expiration time.
        :param session_id: The session ID to store the data under.
        :param data: The session data to store.
        :param expire: Optional expiration time in seconds or a timedelta object.
        :return: True if the operation was successful, False otherwise.
        """
        session_key = f"{SESSION_KEY_PREFIX}:{session_id}"
        return await self.set(session_key, data, expire)

    async def get_session(self, session_id: str) -> Optional[Any]:
        """
        Get a session from Redis by session ID.
        :param session_id: The session ID to retrieve the data for.
        :return: The session data stored under the session ID, or None if not found.
        """
        session_key = f"{SESSION_KEY_PREFIX}:{session_id}"
        return await self.get(session_key)

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session from Redis by session ID.
        :param session_id: The session ID to delete.
        :return: True if the session was deleted, False if it did not exist or an error occurred.
        """
        session_key = f"{SESSION_KEY_PREFIX}:{session_id}"
        return await self.delete(session_key)

    async def session_exists(self, session_id: str) -> bool:
        """
        Check if a session exists in Redis by session ID.
        :param session_id: The session ID to check.
        :return: True if the session exists, False otherwise.
        """
        session_key = f"{SESSION_KEY_PREFIX}:{session_id}"
        return await self.exists(session_key)

    async def blacklist_token(
        self, jti: str, expire: Optional[Union[int, timedelta]] = None
    ) -> bool:
        """
        Blacklist a JWT token in Redis with an optional expiration time.
        :param jti: The JWT ID (jti) of the token to blacklist.
        :param expire: Optional expiration time in seconds or a timedelta object.
        :return: True if the operation was successful, False otherwise.
        """
        return await self.set(f"{BLACKLISTED_TOKEN_PREFIX}:{jti}", "revoked", expire)

    async def is_token_blacklisted(self, jti: str) -> bool:
        """
        Check if a JWT token is blacklisted in Redis.
        :param jti: The JWT ID (jti) of the token to check.
        :return: True if the token is blacklisted, False otherwise.
        """
        return await self.exists(f"{BLACKLISTED_TOKEN_PREFIX}:{jti}")


redis_client = RedisClient()
