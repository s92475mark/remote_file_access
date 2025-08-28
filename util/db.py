from contextlib import contextmanager
from util.global_variable import global_variable

@contextmanager
def get_db_session(db_name: str = "default"):
    db_session = global_variable.database[db_name]()
    try:
        yield db_session
    finally:
        db_session.close()
