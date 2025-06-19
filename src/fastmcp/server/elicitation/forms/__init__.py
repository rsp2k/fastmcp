from .fields.field import Field


class ValidationError(Exception):
    """Raised when field validation fails."""
    pass


__all__ = ["Field", "ValidationError"]
