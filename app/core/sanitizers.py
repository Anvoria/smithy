import re
import html
import unicodedata
from typing import Any, Dict, Optional, Literal
from urllib.parse import urlparse, urlunparse

import bleach  # type: ignore[import]


class BaseSanitizer:
    """Base sanitizer class with common sanitization utilities"""

    @staticmethod
    def strip_whitespace(value: str) -> str:
        """
        Strip leading and trailing whitespace from a string.
        :param value: The input string.
        :return: The trimmed string.
        """
        return value.strip() if value else ""

    @staticmethod
    def normalize_unicode(
        value: str, form: Literal["NFC", "NFD", "NFKC", "NFKD"] = "NFC"
    ) -> str:
        """
        Normalize Unicode characters in a string to a specified form.
        :param value: The input string.
        :param form: The normalization form (default is "NFC").
        :return: The normalized string.
        """
        return unicodedata.normalize(form, value) if value else ""

    @staticmethod
    def remove_null_bytes(value: str) -> str:
        """
        Remove null bytes from a string.
        :param value: The input string.
        :return: The string without null bytes.
        """
        return value.replace("\x00", "") if value else ""


class TextSanitizer(BaseSanitizer):
    """Sanitizer for plain text input"""

    # Common character to remove or replace
    CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]")
    EXCESSIVE_WHITESPACE = re.compile(r"\s+")

    @classmethod
    def sanitize_basic_text(cls, text: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize basic text input by removing control characters and excessive whitespace.
        :param text: The input text.
        :param max_length: Optional maximum length for the sanitized text.
        :return: The sanitized text.
        """
        if not text:
            return ""

        # Basic cleanup
        text = cls.strip_whitespace(text)
        text = cls.normalize_unicode(text)
        text = cls.remove_null_bytes(text)

        # Remove control characters and excessive whitespace
        text = cls.CONTROL_CHARS.sub("", text)
        text = cls.EXCESSIVE_WHITESPACE.sub(" ", text)

        # Limit length if specified
        if max_length is not None:
            text = text[:max_length].strip()

        return text

    @classmethod
    def sanitize_multiline_text(
        cls, text: str, max_length: Optional[int] = None
    ) -> str:
        """
        Sanitize multiline text input by removing control characters and excessive whitespace.
        :param text: The input text.
        :param max_length: Optional maximum length for the sanitized text.
        :return: The sanitized multiline text.
        """
        if not text:
            return ""

        # Split into lines and sanitize each
        lines = text.split("\n")
        sanitized_lines = []

        for line in lines:
            line = cls.strip_whitespace(line)
            line = cls.normalize_unicode(line)
            line = cls.remove_null_bytes(line)
            line = cls.CONTROL_CHARS.sub("", line)

            sanitized_lines.append(line)

        # Join back and handle excessive line breaks
        text = "\n".join(sanitized_lines)

        # Remove excessive consecutive line breaks
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Truncate if needed
        if max_length and len(text) > max_length:
            text = text[:max_length].rstrip()

        return text

    @classmethod
    def sanitize_html_content(
        cls, html_content: str, max_length: Optional[int] = None
    ) -> str:
        """
        Sanitize HTML content by removing unsafe tags and attributes, normalizing Unicode,
        :param html_content: The input HTML content.
        :param max_length: Optional maximum length for the sanitized HTML.
        :return: The sanitized HTML content.
        """
        if not html_content:
            return ""

        # Allowed HTML tags and attributes for rich content
        allowed_tags = [
            "p",
            "br",
            "strong",
            "b",
            "em",
            "i",
            "u",
            "strike",
            "del",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "ul",
            "ol",
            "li",
            "a",
            "blockquote",
            "code",
            "pre",
            "table",
            "thead",
            "tbody",
            "tr",
            "th",
            "td",
        ]

        allowed_attributes = {
            "a": ["href", "title"],
            "blockquote": ["cite"],
            "*": ["class"],  # Allow class on any element
        }

        # Clean HTML
        clean_html = bleach.clean(
            html_content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True,
            strip_comments=True,
        )

        # Additional cleanup
        clean_html = cls.normalize_unicode(clean_html)
        clean_html = cls.remove_null_bytes(clean_html)

        # Truncate if needed
        if max_length and len(clean_html) > max_length:
            clean_html = clean_html[:max_length]
            # Try to avoid cutting in the middle of a tag
            if "<" in clean_html and ">" not in clean_html[clean_html.rfind("<") :]:
                clean_html = clean_html[: clean_html.rfind("<")]

        return clean_html

    @classmethod
    def sanitize_plain_from_html(
        cls, html_content: str, max_length: Optional[int] = None
    ) -> str:
        """
        Sanitize HTML content to plain text by stripping tags and decoding entities.
        :param html_content: The input HTML content.
        :param max_length: Optional maximum length for the sanitized text.
        :return: The sanitized plain text.
        """
        if not html_content:
            return ""

        # Strip all HTML tags
        plain_text = bleach.clean(html_content, tags=[], strip=True)

        # Decode HTML entities
        plain_text = html.unescape(plain_text)

        # Basic text sanitization
        return cls.sanitize_basic_text(plain_text, max_length)


class SlugSanitizer(BaseSanitizer):
    """URL slug sanitizer"""

    @classmethod
    def create_slug_from_text(cls, text: str, max_length: int = 50) -> str:
        """
        Create a URL-friendly slug from a given text.
        :param text: The input text to convert into a slug.
        :param max_length: Maximum length of the slug (default is 50 characters).
        :return: A sanitized slug string.
        """
        if not text:
            return ""

        # Basic cleanup
        text = cls.strip_whitespace(text)
        text = cls.normalize_unicode(text)
        text = text.lower()

        # Replace spaces and special characters with hyphens
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_-]+", "-", text)

        # Remove leading/trailing hyphens
        text = text.strip("-")

        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length].rstrip("-")

        return text or "item"  # Fallback if nothing remains


class URLSanitizer(BaseSanitizer):
    """URL sanitizer and validator"""

    ALLOWED_SCHEMES = {"http", "https", "ftp", "ftps"}
    DANGEROUS_PROTOCOLS = {"javascript", "data", "vbscript", "file"}

    @classmethod
    def sanitize_url(cls, url: str, allowed_schemes: Optional[set] = None) -> str:
        """
        Sanitize and validate a URL, ensuring it uses allowed protocols and is well-formed.
        :param url: The input URL to sanitize.
        :param allowed_schemes: Optional set of allowed URL schemes.
        :return: A sanitized URL string.
        """
        if not url:
            return ""

        url = cls.strip_whitespace(url)
        url = cls.normalize_unicode(url)

        # Parse URL
        try:
            parsed = urlparse(url)
        except Exception:
            raise ValueError("Invalid URL format")

        # Check scheme
        allowed = allowed_schemes or cls.ALLOWED_SCHEMES
        if parsed.scheme.lower() not in allowed:
            if parsed.scheme.lower() in cls.DANGEROUS_PROTOCOLS:
                raise ValueError(f"Dangerous protocol: {parsed.scheme}")
            raise ValueError(f"Unsupported protocol: {parsed.scheme}")

        # Reconstruct clean URL
        clean_url = urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment,
            )
        )

        return clean_url


class EmailSanitizer(BaseSanitizer):
    """Email address sanitizer"""

    @classmethod
    def sanitize_email(cls, email: str) -> str:
        """
        Sanitize an email address by stripping whitespace, normalizing Unicode,
        :param email: The input email address to sanitize.
        :return: A sanitized email address string.
        """
        if not email:
            return ""

        email = cls.strip_whitespace(email)
        email = cls.normalize_unicode(email)
        email = email.lower()

        # Remove any potentially dangerous characters
        email = re.sub(r"[^\w@.-]", "", email)

        return email


class FilenameSanitizer(BaseSanitizer):
    """Filename sanitizer"""

    DANGEROUS_EXTENSIONS = {
        ".exe",
        ".bat",
        ".cmd",
        ".com",
        ".pif",
        ".scr",
        ".vbs",
        ".js",
        ".jar",
        ".php",
        ".asp",
        ".aspx",
        ".jsp",
        ".py",
        ".rb",
        ".sh",
    }

    @classmethod
    def sanitize_filename(cls, filename: str, max_length: int = 255) -> str:
        """
        Sanitize a filename by removing dangerous characters, normalizing Unicode,
        and ensuring it does not exceed a maximum length.
        :param filename: The input filename to sanitize.
        :param max_length: Maximum length of the sanitized filename (default is 255 characters).
        :return: A sanitized filename string.
        """
        if not filename:
            return ""

        filename = cls.strip_whitespace(filename)
        filename = cls.normalize_unicode(filename)

        # Remove/replace dangerous characters
        filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
        filename = re.sub(r"[\x00-\x1f]", "", filename)

        # Remove leading dots and spaces
        filename = filename.lstrip(". ")

        # Check for dangerous extensions
        lower_filename = filename.lower()
        for ext in cls.DANGEROUS_EXTENSIONS:
            if lower_filename.endswith(ext):
                filename = filename[: -len(ext)] + "_" + ext[1:]

        # Truncate if needed
        if len(filename) > max_length:
            name, ext = filename.rsplit(".", 1) if "." in filename else (filename, "")
            max_name_length = max_length - len(ext) - 1 if ext else max_length
            filename = name[:max_name_length] + ("." + ext if ext else "")

        return filename or "file"


class JSONSanitizer(BaseSanitizer):
    """JSON data sanitizer"""

    @classmethod
    def sanitize_json_strings(cls, data: Any, max_string_length: int = 1000) -> Any:
        """
        Recursively sanitize JSON strings by applying basic text sanitization.
        :param data: The input data (can be a string, dict, list, etc.).
        :param max_string_length: Maximum length for sanitized strings (default is 1000 characters).
        :return: Sanitized data with strings processed.
        """
        if isinstance(data, str):
            return TextSanitizer.sanitize_basic_text(data, max_string_length)
        elif isinstance(data, dict):
            return {
                cls.sanitize_json_strings(k, 100): cls.sanitize_json_strings(
                    v, max_string_length
                )
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [cls.sanitize_json_strings(item, max_string_length) for item in data]
        else:
            return data


class QuerySanitizer(BaseSanitizer):
    """Database query parameter sanitizer"""

    SQL_INJECTION_PATTERNS = [
        r"union\s+select",
        r"insert\s+into",
        r"delete\s+from",
        r"update\s+.*\s+set",
        r"drop\s+table",
        r"drop\s+database",
        r"create\s+table",
        r"alter\s+table",
        r"exec\s*\(",
        r"script\s*>",
        r"javascript\s*:",
        r"expression\s*\(",
        r"vbscript\s*:",
        r"onload\s*=",
        r"onerror\s*=",
    ]

    @classmethod
    def sanitize_search_query(cls, query: str, max_length: int = 100) -> str:
        """
        Sanitize a search query by removing potentially dangerous characters,
        normalizing Unicode, and checking for SQL injection patterns.
        :param query: The input search query to sanitize.
        :param max_length: Maximum length of the sanitized query (default is 100 characters).
        :return: A sanitized search query string.
        """
        if not query:
            return ""

        query = cls.strip_whitespace(query)
        query = cls.normalize_unicode(query)

        # Check for SQL injection patterns
        query_lower = query.lower()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query_lower):
                raise ValueError("Invalid characters in search query")

        # Remove potentially dangerous characters
        query = re.sub(r"[;\'\"\\]", "", query)

        # Limit length
        if len(query) > max_length:
            query = query[:max_length]

        return query


class ComprehensiveSanitizer:
    """Main sanitizer that combines all sanitization methods"""

    @staticmethod
    def sanitize_user_input(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize user input data by applying appropriate sanitization methods
        :param data: A dictionary containing user input data with various fields.
        :return: A dictionary with sanitized values based on field types.
        """
        sanitized = {}

        for key, value in data.items():
            if isinstance(value, str):
                # Determine sanitization method based on field name
                if "email" in key.lower():
                    sanitized[key] = EmailSanitizer.sanitize_email(value)
                elif "url" in key.lower() or "link" in key.lower():
                    try:
                        sanitized[key] = URLSanitizer.sanitize_url(value)
                    except ValueError:
                        sanitized[key] = ""  # Invalid URL becomes empty string
                elif "slug" in key.lower():
                    sanitized[key] = SlugSanitizer.create_slug_from_text(value)
                elif "filename" in key.lower() or "file" in key.lower():
                    sanitized[key] = FilenameSanitizer.sanitize_filename(value)
                elif "html" in key.lower() or "content" in key.lower():
                    sanitized[key] = TextSanitizer.sanitize_html_content(value)
                elif "description" in key.lower() or "bio" in key.lower():
                    sanitized[key] = TextSanitizer.sanitize_multiline_text(value)
                elif "search" in key.lower() or "query" in key.lower():
                    sanitized[key] = QuerySanitizer.sanitize_search_query(value)
                else:
                    # Default text sanitization
                    sanitized[key] = TextSanitizer.sanitize_basic_text(value)
            elif isinstance(value, dict):
                sanitized[key] = JSONSanitizer.sanitize_json_strings(value)
            elif isinstance(value, list):
                sanitized[key] = JSONSanitizer.sanitize_json_strings(value)
            else:
                sanitized[key] = value

        return sanitized


__all__ = [
    "BaseSanitizer",
    "TextSanitizer",
    "SlugSanitizer",
    "URLSanitizer",
    "EmailSanitizer",
    "FilenameSanitizer",
    "JSONSanitizer",
    "QuerySanitizer",
    "ComprehensiveSanitizer",
]
