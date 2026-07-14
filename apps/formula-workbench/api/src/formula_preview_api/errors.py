from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldError:
    path: str
    code: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "code": self.code, "message": self.message}


class PreviewAPIError(ValueError):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        fields: list[FieldError] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.fields = tuple(fields or ())

    def payload(self) -> dict[str, object]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "fields": [field.as_dict() for field in self.fields],
            }
        }
