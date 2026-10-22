class AppError(Exception):
    status_code = 500
    default_message = "Something went wrong. Please try again."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidCredentialsError(AppError):
    status_code = 401
    default_message = "Invalid credentials."


class ConflictError(AppError):
    status_code = 409
    default_message = "That already exists"


class NotFoundError(AppError):
    status_code = 404
    default_message = "The item you were looking for was not found"


class BadRequestError(AppError):
    status_code = 400
    default_message = "Bad request"


class NotAuthorisedError(AppError):
    status_code = 403
    default_message = "Not authorised"


class ServiceUnavailableError(AppError):
    status_code = 503
    default_message = "This service is not available right now."


class TooManyRequestsError(AppError):
    status_code = 429
    default_message = "Too many requests"


class DemoReadOnlyError(AppError):
    status_code = 403
    default_message = (
        "The shared demo is read-only. Register to upload and manage your own files."
    )


class ProcessingLimitError(Exception):
    """A file cannot be processed (too large, unreadable). The message is safe to show users."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)
