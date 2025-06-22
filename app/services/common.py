from typing import Optional


class CommonService:
    """
    Common service class providing utility methods for serialization and other common tasks.
    """

    @staticmethod
    def serialize_pydantic_to_dict(obj) -> Optional[dict]:
        """
        Convert Pydantic model to dict for JSON serialization
        """
        if obj is None:
            return None
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        elif hasattr(obj, "dict"):
            return obj.dict()
        elif isinstance(obj, dict):
            return obj
        else:
            return {}
