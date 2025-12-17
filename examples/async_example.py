from fastapi import FastAPI
from fastapi_auto_crud import generate_crud_routes

app = FastAPI()
app.include_router(
    generate_crud_routes(database_url="sqlite+aiosqlite:///./async_example.db", base_url="/api")
)

# Run with: uvicorn async_example:app --reload