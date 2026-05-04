from .session import engine
from .base import Base
from ..models import entities  # noqa

def init_db():
    Base.metadata.create_all(bind=engine)
