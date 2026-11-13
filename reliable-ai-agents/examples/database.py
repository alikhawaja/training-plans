"""Small SQL boundary: tools can read only the approved evidence view."""

import os
import re
from contextlib import contextmanager

import pymssql

from settings import required


@contextmanager
def connection(*, admin: bool = False, database: str = "SupportLab"):
    host = os.environ.get("SQL_HOST", "127.0.0.1")
    if host not in {"127.0.0.1", "localhost", "sql"}:
        raise ValueError("SQL_HOST must be loopback or the Compose sql service")
    conn = pymssql.connect(
        server=host,
        port=os.environ.get("SQL_PORT", "14330"),
        user="sa" if admin else "lab_reader",
        password=required("MSSQL_SA_PASSWORD" if admin else "SQL_READER_PASSWORD"),
        database=database,
        login_timeout=5,
        timeout=5,
        autocommit=True,
        as_dict=True,
    )
    try:
        yield conn
    finally:
        conn.close()


def order_evidence(order_id: str) -> dict:
    if not re.fullmatch(r"ORD-\d{4}", order_id):
        raise ValueError("order_id must have the form ORD-1001")
    with connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT TOP (1) order_id, customer_ref, payment_status, shipment_status "
                "FROM lab.order_evidence WHERE order_id = %s",
                (order_id,),
            )
            row = cursor.fetchone()
    return {"source": f"sql:lab.order_evidence:{order_id}", "order": row}


def seed_sql() -> None:
    password = required("SQL_READER_PASSWORD")
    if len(password) < 20:
        raise ValueError("Generate a strong SQL_READER_PASSWORD with manage.py configure")
    escaped = password.replace("'", "''")
    with connection(admin=True, database="master") as conn:
        with conn.cursor() as cursor:
            cursor.execute("IF DB_ID('SupportLab') IS NULL CREATE DATABASE SupportLab")
            cursor.execute(
                "IF SUSER_ID('lab_reader') IS NULL "
                f"CREATE LOGIN lab_reader WITH PASSWORD = '{escaped}'"
            )
            cursor.execute(f"ALTER LOGIN lab_reader WITH PASSWORD = '{escaped}'")
    with connection(admin=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute("IF SCHEMA_ID('lab') IS NULL EXEC('CREATE SCHEMA lab')")
            cursor.execute(
                "IF OBJECT_ID('dbo.orders') IS NULL CREATE TABLE dbo.orders ("
                "order_id varchar(20) PRIMARY KEY, customer_ref varchar(40) NOT NULL,"
                "payment_status varchar(20) NOT NULL, shipment_status varchar(20) NOT NULL)"
            )
            for row in [
                ("ORD-1001", "CUSTOMER-A", "captured", "absent"),
                ("ORD-1002", "CUSTOMER-B", "captured", "shipped"),
                ("ORD-1003", "CUSTOMER-C", "pending", "absent"),
            ]:
                cursor.execute(
                    "MERGE dbo.orders AS target USING "
                    "(SELECT %s AS order_id, %s AS customer_ref, %s AS payment_status,"
                    "%s AS shipment_status) AS source ON target.order_id=source.order_id "
                    "WHEN MATCHED THEN UPDATE SET customer_ref=source.customer_ref,"
                    "payment_status=source.payment_status,shipment_status=source.shipment_status "
                    "WHEN NOT MATCHED THEN INSERT VALUES "
                    "(source.order_id,source.customer_ref,source.payment_status,source.shipment_status);",
                    row,
                )
            cursor.execute(
                "CREATE OR ALTER VIEW lab.order_evidence AS "
                "SELECT order_id,customer_ref,payment_status,shipment_status FROM dbo.orders"
            )
            cursor.execute(
                "IF USER_ID('lab_reader') IS NULL CREATE USER lab_reader FOR LOGIN lab_reader"
            )
            cursor.execute("GRANT SELECT ON OBJECT::lab.order_evidence TO lab_reader")
            cursor.execute("DENY SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.orders TO lab_reader")
