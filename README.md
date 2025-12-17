# fastapi-auto-restful

Automatically generate RESTful CRUD APIs from your database tables.

## ✨ Features

- **Sync & Async** support (SQLAlchemy 2.0)
- **Pagination**: `{"items": [...], "total": 100, "skip": 0, "limit": 10}`
- **Query filtering**: `?name=John&age__gt=18`
- **Nested responses** for foreign keys
- Works with **PostgreSQL, MySQL, SQLite**

## 🚀 Install

```bash
pip install fastapi-auto-restful