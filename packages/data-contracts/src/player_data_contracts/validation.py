class ContractValidationError(ValueError):
    """Raised when data does not satisfy a versioned contract."""


def safe_repr(value: object) -> str:
    """Render malformed contract values without leaking conversion errors."""
    try:
        return repr(value)
    except (OverflowError, ValueError):
        return f"<{type(value).__name__} outside supported representation>"
