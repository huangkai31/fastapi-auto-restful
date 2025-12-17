__version__ = "0.3.0"

from .auto_router import generate_crud_routes
from .schemas import PaginatedResponse

__all__ = ["generate_crud_routes", "PaginatedResponse"]