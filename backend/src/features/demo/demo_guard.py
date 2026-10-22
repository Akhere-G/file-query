import inspect
from functools import wraps

from src.exceptions import DemoReadOnlyError
from src.features.auth.user_model import User


def block_demo(func):
    """Refuse the call when the signed-in user is the shared demo account.

    Put it directly above a synchronous route function, under the router/limiter decorators.
    The function needs a parameter annotated `User`; this is checked when the module loads,
    so a route that cannot be protected fails at startup instead of silently being open.
    """
    if inspect.iscoroutinefunction(func):
        raise TypeError(f"block_demo only supports sync routes: {func.__name__}")

    user_params = [
        name
        for name, parameter in inspect.signature(func).parameters.items()
        if parameter.annotation is User
    ]
    if not user_params:
        raise TypeError(f"{func.__name__} needs a `user: User` parameter to use block_demo")

    @wraps(func)
    def wrapper(*args, **kwargs):
        user = kwargs.get(user_params[0])
        if user is None or user.is_demo:
            raise DemoReadOnlyError()
        return func(*args, **kwargs)

    return wrapper
