class AppError(Exception):
    status_code = 500
    default_message = "Something went wrong. Please try again."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidCredentialsError(AppError):
    status_code = 401
    default_message = "Invalid credentials."


class NotFoundError(AppError):
    status_code = 404
    default_message = "The item you were looking for was not found"


class BadRequestError(AppError):
    status_code = 400
    default_message = "Bad request"
