"""`Redshift` facilities."""

import json
import os
import typing

from redshift_connector import Connection
from redshift_connector import connect as redshift
from redshift_connector.cursor import Cursor

from ..utils import clean_query, fetch_parents

redshift_config = {
    "user": os.environ["REDSHIFT_USER"],
    "password": os.environ["REDSHIFT_PASSWORD"],
    "host": os.environ["REDSHIFT_HOST"],
    "port": int(os.environ.get("REDSHIFT_PORT", 5439)),
    "database": os.environ["REDSHIFT_DB"],
}


def fetch_objects(
    cursor: Cursor, objects: dict[str, typing.Any] = {}
) -> tuple[dict[str, Connection], dict[str, typing.Any]]:
    """List all objects in all `Redshift` databases.

    Parameters
    ----------
    cursor : redshift_connector.cursor.Cursor
        Cursor to use to run the query.
    objects : dict[str, typing.Any]
        Empty dictionary of objets encountered.

    Returns
    -------
    : dict[str, redshift_connector.connection.Connection]
        Dictionary of connection object for each database encountered.
    : dict[str, typing.Any]
        Dictionary of objects encountered, indexed by their respective long names.

    Notes
    -----
    Performing the following query:
    ```sql
    select
        database_name,
        schema_name,
        table_name,
        table_type
    from
        pg_catalog.svv_all_tables
    where
        schema_name not in ('information_schema', 'pg_catalog')
        and substring(table_name, 1, 8) <> 'mv_tbl__'
    order by
        database_name, schema_name, table_name
    ```
    """
    connections: dict[str, Connection] = {}

    q = """
    select
        database_name,
        schema_name,
        table_name,
        table_type
    from
        pg_catalog.svv_all_tables
    where
        schema_name not in ('information_schema', 'pg_catalog')
        and substring(table_name, 1, 8) <> 'mv_tbl__'
    order by
        database_name, schema_name, table_name
    """

    cursor.execute(q)

    for d, s, n, t in cursor.fetchall():

        # create a new connection associated with that database
        if d not in connections:
            redshift_config["database"] = d
            connections[d] = redshift(**redshift_config)

        # save the object
        o = f"{d}.{s}.{n}"
        objects[o] = {"name": n, "schema": s, "database": d, "type": t}

    return connections, objects


def fetch_ddl(cursor: Cursor, n: str, s: str, d: str, t: str) -> str:
    """Fetch the DDL of an object.

    Parameters
    ----------
    cursor : redshift_connector.cursor.Cursor
        Cursor to use to run the query.
    n : str
        Name of the object.
    s : str
        Name of the schema hosting the object.
    d : str
        Name of the database hosting the schema.
    t : str
        One of `external table`, `table` or `view` (last one accounting for materialized
        views as well).

    Returns
    -------
    : str
        DDL of the object.

    Notes
    -----
    Performing the following [example] query:
    ```sql
    show external table schema.table
    ```
    """
    try:
        cursor.execute(f"show {t} {s}.{n}")
        return cursor.fetchone()[0]
    except:
        return "-- UNABLE TO FETCH"


def fetch_columns(cursor: Cursor, n: str, s: str, d: str) -> list[dict[str, str]]:
    """List all columns from an object.

    Parameters
    ----------
    cursor : redshift_connector.cursor.Cursor
        Cursor to use to run the query.
    n : str
        Name of the object.
    s : str
        Name of the schema hosting the object.
    d : str
        Name of the database hosting the schema.

    Returns
    -------
    : list[dict[str, str]]
        Dictionary describing the object columns (name and datatypes).

    Notes
    -----
    Performing the following [example] query:
    ```sql
    select
        column_name,
        data_type
    from
        pg_catalog.svv_all_columns
    where
        database_name = 'database'
        and schema_name = 'schema'
        and table_name = 'table'
    order by
        ordinal_position
    ```
    """
    q = f"""
    select
        column_name,
        data_type
    from
        pg_catalog.svv_all_columns
    where
        database_name = '{d}'
        and schema_name = '{s}'
        and table_name = '{n}'
    order by
        ordinal_position
    """

    try:
        cursor.execute(q)
        return [{"name": n, "datatype": t} for n, t in cursor.fetchall()]
    except:
        return []


def fetch_details() -> dict[str, typing.Any]:
    """List all objects in all databases and fetch their respective DDLs and columns.

    Returns
    -------
    : dict[str, typing.Any]
        Dictionary of objects encountered, indexed by their respective long names.
    """
    # fetching the list of all objects does not require a particular database
    with redshift(**redshift_config) as connection:
        with connection.cursor() as cursor:
            connections, objects = fetch_objects(cursor)

    paths = list(objects.keys())

    # loop over each object and fetch its ddl and columns
    for i, o in enumerate(objects):
        n = objects[o]["name"]
        s = objects[o]["schema"]
        d = objects[o]["database"]
        t = objects[o]["type"]

        with connections[d].cursor() as cursor:
            l = fetch_ddl(cursor, n, s, d, t)
            c = fetch_columns(cursor, n, s, d)
            p = fetch_parents(clean_query(l), paths, d)  # clean the query on the way

            objects[o].update({"ddl": l, "columns": c, "parents": p})

    # close all created connections
    for connection in connections.values():
        connection.close()

    return objects


if __name__ == "__main__":
    print(json.dumps(fetch_details()))
