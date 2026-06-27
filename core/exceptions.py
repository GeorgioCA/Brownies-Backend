from starlette.exceptions import HTTPException


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str = "", code: str = "error", headers: dict = None):
        self.code = code
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class AuthException(AppException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(401, detail, "auth_error")


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Access denied"):
        super().__init__(403, detail, "forbidden")


class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(404, detail, "not_found")


class ConflictException(AppException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(409, detail, "conflict")


class ValidationException(AppException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(422, detail, "validation_error")


class RateLimitException(AppException):
    def __init__(self, detail: str = "Too many requests", retry_after: int = 60):
        headers = {"Retry-After": str(retry_after)}
        super().__init__(429, detail, "rate_limit", headers=headers)


class PaymentRequiredException(AppException):
    def __init__(self, detail: str = "Premium subscription required"):
        super().__init__(402, detail, "payment_required")


class VerificationRequiredException(AppException):
    def __init__(self, detail: str = "Phone and photo verification required"):
        super().__init__(403, detail, "verification_required")
