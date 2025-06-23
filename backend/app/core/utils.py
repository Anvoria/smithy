import hashlib
import urllib.parse
from typing import Literal


class AvatarUtils:
    """Utilities for generating and managing user avatars."""

    GRAVATAR_BASE_URL = "https://www.gravatar.com/avatar/"

    @staticmethod
    def get_gravatar_url(
        email: str,
        size: int = 200,
        default: Literal[
            "mp", "identicon", "monsterid", "wavatar", "retro", "robohash", "blank"
        ] = "mp",
        rating: Literal["g", "pg", "r", "x"] = "g",
        force_default: bool = False,
    ) -> str:
        """
        Generate a Gravatar URL for the given email address.

        :param email: User's email address.
        :param size: Size of the avatar in pixels (1-2048).
        :param default: Default avatar type if no Gravatar is found
        - options are 'mp', 'identicon', 'monsterid', 'wavatar', 'retro', 'robohash', 'blank'.
        :param rating: Gravatar rating - 'g', 'pg', 'r', 'x'.
        :param force_default: If True, forces the default avatar even if a Gravatar exists.
        :return: Full Gravatar URL.
        """
        normalized_email = email.strip().lower()

        email_hash = hashlib.md5(normalized_email.encode("utf-8")).hexdigest()

        # Build query parameters
        params = {
            "s": str(max(1, min(size, 2048))),  # Ensure size is between 1 and 2048
            "d": default,
            "r": rating,
        }

        if force_default:
            params["f"] = "y"

        # Construct the full URL with query parameters
        query_string = urllib.parse.urlencode(params)
        return f"{AvatarUtils.GRAVATAR_BASE_URL}{email_hash}?{query_string}"

    @staticmethod
    def get_gravatar_profile_url(email: str) -> str:
        """
        Get Gravatar profile URL for given email.
        :param email: User's email address.
        :return: Gravatar profile URL.
        """
        email_normalized = email.lower().strip()
        email_hash = hashlib.md5(email_normalized.encode("utf-8")).hexdigest()
        return f"https://www.gravatar.com/{email_hash}"
