from functools import wraps
from flask import current_app


def with_storage(storage):
    def _wrapper(f):
        @wraps(f)
        def _wrapped(*args, **kwargs):
            strg = storage.bind(current_app.config)
            return f(*args, storage=strg, **kwargs)
        return _wrapped
    return _wrapper
