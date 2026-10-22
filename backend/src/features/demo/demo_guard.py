from functools import wraps

from src.exceptions import DemoReadOnlyError


def block_demo(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if kwargs["user"].is_demo:
            raise DemoReadOnlyError()
        return func(*args, **kwargs)

    return wrapper
