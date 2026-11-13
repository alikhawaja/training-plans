"""Local order API. Synthetic data and a public demonstration token only."""

import logging
import os
import secrets
import sqlite3
import uuid
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime, timezone
from http import HTTPStatus
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("uvicorn.error")
Status = Literal["pending", "confirmed", "shipped", "cancelled"]
Item = Annotated[str, Field(min_length=1, max_length=80)]
Quantity = Annotated[int, Field(strict=True, ge=1, le=100)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class OrderCreate(Contract):
    reference: str = Field(min_length=1, max_length=40, pattern=r"^[a-zA-Z0-9_-]+$")
    item: Item
    quantity: Quantity


class OrderReplace(Contract):
    item: Item
    quantity: Quantity
    status: Status


class OrderPatch(Contract):
    item: Item | None = None
    quantity: Quantity | None = None
    status: Status | None = None

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("explicit null is not supported for these fields")
        return self


class Order(Contract):
    id: str
    reference: str
    item: str
    quantity: int
    status: Status
    created_at: str
    version: int


class OrderPage(Contract):
    items: list[Order]
    total: int
    limit: int
    offset: int
    next: str | None


class Problem(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    request_id: str
    errors: list[dict[str, object]] | None = None


def create_app(db_path=None, token=None):
    database = Path(db_path or os.environ.get("TRAINING_DB", ".state/rest-api.db"))
    expected_token = token if token is not None else os.environ.get(
        "TRAINING_API_TOKEN", "workshop-demo-token"
    )
    if not expected_token:
        raise ValueError("TRAINING_API_TOKEN must not be empty")

    @contextmanager
    def connect():
        connection = sqlite3.connect(database, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @asynccontextmanager
    async def lifespan(_):
        database.parent.mkdir(parents=True, exist_ok=True)
        with connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY, reference TEXT NOT NULL UNIQUE,
                    item TEXT NOT NULL, quantity INTEGER NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL,
                    version INTEGER NOT NULL
                )"""
            )
        yield

    app = FastAPI(
        title="Order API workshop",
        version="1.0.0",
        description="Local HTTP teaching API; use only synthetic data.",
        lifespan=lifespan,
        responses={
            status: {
                "description": HTTPStatus(status).phrase,
                "content": {"application/problem+json": {"schema": Problem.model_json_schema()}},
            }
            for status in (401, 404, 405, 409, 412, 422, 428, 503)
        },
    )

    def problem(request, status, detail, headers=None, errors=None):
        body = {
            "type": "about:blank",
            "title": HTTPStatus(status).phrase,
            "status": status,
            "detail": detail,
            "instance": request.url.path,
            "request_id": request.state.request_id,
        }
        if errors is not None:
            body["errors"] = errors
        return JSONResponse(
            body, status_code=status, headers=headers, media_type="application/problem+json"
        )

    @app.middleware("http")
    async def trace_request(request: Request, call_next):
        request.state.request_id = str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        if "Cache-Control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"
        logger.info(
            "request_id=%s method=%s path=%s status=%s",
            request.state.request_id, request.method, request.url.path, response.status_code,
        )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, error):
        return problem(request, error.status_code, str(error.detail), error.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        return problem(
            request, 422, "Request does not match the API contract.",
            errors=[{"location": list(e["loc"]), "message": e["msg"]} for e in error.errors()],
        )

    @app.exception_handler(sqlite3.OperationalError)
    async def database_error(request, error):
        logger.error("request_id=%s database operation failed: %s", request.state.request_id, error)
        return problem(request, 503, "Database temporarily unavailable.", {"Retry-After": "1"})

    bearer = HTTPBearer(auto_error=False, description="Public local demonstration token only.")

    def authenticate(
        credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    ):
        if credentials is None or not secrets.compare_digest(
            credentials.credentials.encode("utf-8"), expected_token.encode("utf-8")
        ):
            raise HTTPException(
                401, "Supply the workshop Bearer token.", headers={"WWW-Authenticate": "Bearer"}
            )

    def lookup(connection, order_id):
        row = connection.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Order not found.")
        return dict(row)

    def etag(order):
        return f'"{order["id"]}:{order["version"]}"'

    def require_match(header, order):
        if header is None:
            raise HTTPException(428, "Read the order and supply its ETag in If-Match.")
        if header.strip() != "*" and etag(order) not in [v.strip() for v in header.split(",")]:
            raise HTTPException(412, "Order changed; read it again before updating.")

    @app.get("/health")
    def health():
        with connect() as connection:
            connection.execute("SELECT 1 FROM orders LIMIT 1").fetchone()
        return {"status": "ok"}

    authorized = [Depends(authenticate)]

    @app.post("/api/v1/orders", status_code=201, response_model=Order, dependencies=authorized)
    def create_order(order: OrderCreate, response: Response):
        record = {
            "id": str(uuid.uuid4()), **order.model_dump(), "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(), "version": 1,
        }
        with connect() as connection:
            try:
                connection.execute(
                    "INSERT INTO orders VALUES (:id,:reference,:item,:quantity,:status,:created_at,:version)",
                    record,
                )
            except sqlite3.IntegrityError as error:
                if getattr(error, "sqlite_errorname", "") != "SQLITE_CONSTRAINT_UNIQUE":
                    raise
                raise HTTPException(409, "An order with this reference already exists.") from error
        response.headers["Location"] = f'/api/v1/orders/{record["id"]}'
        response.headers["ETag"] = etag(record)
        return record

    @app.get("/api/v1/orders", response_model=OrderPage, dependencies=authorized)
    def list_orders(
        limit: Annotated[int, Query(ge=1, le=50)] = 10,
        offset: Annotated[int, Query(ge=0)] = 0,
        status: Status | None = None,
    ):
        where = " WHERE status = ?" if status is not None else ""
        parameters = (status,) if status is not None else ()
        with connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM orders" + where, parameters).fetchone()[0]
            rows = connection.execute(
                "SELECT * FROM orders" + where + " ORDER BY created_at, id LIMIT ? OFFSET ?",
                (*parameters, limit, offset),
            ).fetchall()
        next_page = None
        if offset + limit < total:
            next_page = f"/api/v1/orders?limit={limit}&offset={offset + limit}"
            if status is not None:
                next_page += f"&status={status}"
        return {"items": [dict(row) for row in rows], "total": total,
                "limit": limit, "offset": offset, "next": next_page}

    @app.get("/api/v1/orders/{order_id}", response_model=Order, dependencies=authorized)
    def get_order(
        order_id: uuid.UUID, response: Response,
        if_none_match: Annotated[str | None, Header()] = None,
    ):
        with connect() as connection:
            record = lookup(connection, str(order_id))
        headers = {"ETag": etag(record), "Cache-Control": "private, max-age=0, must-revalidate"}
        candidates = [v.strip().removeprefix("W/") for v in (if_none_match or "").split(",")]
        if "*" in candidates or etag(record) in candidates:
            return Response(status_code=304, headers=headers)
        response.headers.update(headers)
        return record

    def update(order_id, fields, if_match, response):
        with connect() as connection:
            # Hold the write reservation across the read and update to avoid lost updates.
            connection.execute("BEGIN IMMEDIATE")
            record = lookup(connection, str(order_id))
            require_match(if_match, record)
            if any(record[key] != value for key, value in fields.items()):
                record.update(fields)
                record["version"] += 1
                connection.execute(
                    """UPDATE orders SET item=:item, quantity=:quantity,
                       status=:status, version=:version WHERE id=:id""", record,
                )
        response.headers["ETag"] = etag(record)
        return record

    @app.put("/api/v1/orders/{order_id}", response_model=Order, dependencies=authorized)
    def replace_order(
        order_id: uuid.UUID, order: OrderReplace, response: Response,
        if_match: Annotated[str | None, Header()] = None,
    ):
        return update(order_id, order.model_dump(), if_match, response)

    @app.patch("/api/v1/orders/{order_id}", response_model=Order, dependencies=authorized)
    def patch_order(
        order_id: uuid.UUID, order: OrderPatch, response: Response,
        if_match: Annotated[str | None, Header()] = None,
    ):
        return update(order_id, order.model_dump(exclude_unset=True), if_match, response)

    @app.delete("/api/v1/orders/{order_id}", status_code=204, dependencies=authorized)
    def delete_order(
        order_id: uuid.UUID, if_match: Annotated[str | None, Header()] = None,
    ):
        with connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            record = lookup(connection, str(order_id))
            require_match(if_match, record)
            connection.execute("DELETE FROM orders WHERE id = ?", (str(order_id),))
        return Response(status_code=204)

    return app


app = create_app()
