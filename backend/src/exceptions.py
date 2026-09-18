class AppError(Exception):
    status_code = 500
    default_message = "Something went wrong. Please try again."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class InvalidCredentialsError(AppError):
    status_code = 401
    default_message = "Invalid credentials."
