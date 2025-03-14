from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Model for error responses"""

    error: str
