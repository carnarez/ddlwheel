"""`Redshift` facilities."""

import json
import os
import typing

from redshift_connector import Connection
from redshift_connector import connect as redshift
from redshift_connector.cursor import Cursor

from ..utils import clean_query, fetch_children, fetch_parents

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
    objects : dict[str, str]
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
        table_name as object_name,
        table_type as object_type
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
        table_name as object_name,
        table_type as object_type
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


def fetch_procs(
    cursor: Cursor, d: str, procs: dict[str, typing.Any] = {}
) -> dict[str, typing.Any]:
    """List all stored procedures in all schemas of a `Redshift` database.

    Parameters
    ----------
    cursor : redshift_connector.cursor.Cursor
        Cursor to use to run the query.
    d : str
        Name of the database hosting the schema.
    procs : dict[str, typing.Any]
        Empty dictionary of procedures encountered.

    Returns
    -------
    : dict[str, typing.Any]
        Dictionary of procedures encountered, indexed by their respective long names.

    Notes
    -----
    Performing the following query:
    ```sql
    select
        'database' as database_name,
        n.nspname as schema_name,
        p.proname as object_name,
        'PROCEDURE' as object_type
    from
        pg_catalog.pg_namespace n
    join
        pg_catalog.pg_proc p
    on
        pronamespace = n.oid
    where
        proowner = current_user_id
        and proname <> 'get_result_set'
    ```
    """
    # https://stackoverflow.com/a/62257907
    q = f"""
    select
        '{d}' as database_name,
        n.nspname as schema_name,
        p.proname as object_name,
        'PROCEDURE' as object_type
    from
        pg_catalog.pg_namespace n
    join
        pg_catalog.pg_proc p
    on
        pronamespace = n.oid
    where
        proowner = current_user_id
        and proname <> 'get_result_set'
    """

    cursor.execute(q)

    for d, s, n, t in cursor.fetchall():

        # store the proc
        o = f"{d}.{s}.{n}"
        procs[o] = {"name": n, "schema": s, "database": d, "type": t}

    return procs


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
    except Exception:
        return "-- UNABLE TO FETCH"


def fetch_columns(
    cursor: Cursor, n: str, s: str, d: str, root_dir: str
) -> list[dict[str, str]]:
    """List all columns from an object and sample associated data.

    If a `sample.sql` file is found in the given directory it is used to sample the
    various columns of the object. Do NOT make it random! Otherwise each time this
    script will run a new `README.md` will have to be committed.

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
    root_dir : str
        Directory in which to write content/fetch content from.

    Returns
    -------
    : list[dict[str, str]]
        Dictionary describing the object columns (name, datatypes, samples if a
        `sample.sql` is provided).

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
        c = cursor.fetchall()
    except Exception:
        c = []

    return [{"name": n_, "datatype": t_, "sample": s_} for n_, t_, s_ in c]


def fetch_details(
    root_dir: str = "./", write_dict: str = "objects.json"
) -> dict[str, typing.Any]:
    """List all objects in the database, fetch their DDLs and sample their data.

    Parameters
    ----------
    root_dir : str
        Directory to write content in/fetch content from.
    write_dict : str
        If provided, write the details JSON to that path.

    Returns
    -------
    : dict[str, typing.Any]
        Dictionary of objects encountered, indexed by their respective long names.
    """
    # fetching the list of all objects does not require a particular database
    with redshift(**redshift_config) as connection:
        with connection.cursor() as cursor:
            connections, objects = fetch_objects(cursor)

    # fetching the list of all stored procedures *does* require a particular database
    # the next few lines clobber existing objects in the database
    for d in connections:
        with connections[d].cursor() as cursor:
            objects = fetch_procs(cursor, d, objects)

    objects = dict(sorted(objects.items()))
    paths = list(objects.keys())

    # loop over each object and fetch its ddl, columns an data samples, and extract
    # parents from the former
    N = len(objects)
    for i, o in enumerate(objects):
        n = objects[o]["name"]
        s = objects[o]["schema"]
        d = objects[o]["database"]
        t = objects[o]["type"]

        with connections[d].cursor() as cursor:
            l = fetch_ddl(cursor, n, s, d, t)
            q = clean_query(l)  # clean the query
            m = f"{(i + 1)*100/N:.0f}% {d}.{s}.{n}"

            # parent details
            p = fetch_parents(q, paths, d)

            # column details
            if t == "PROCEDURE":
                c = None
                k = fetch_children(q, paths, d)
                m += f": {len(p)} parents and {len(k)} children fetched."
            else:
                c = fetch_columns(cursor, n, s, d, root_dir)
                k = None
                m += f": {len(c)} columns and {len(p)} parents fetched."

            objects[o].update({"ddl": l, "columns": c, "parents": p, "children": k})

    # close all created connections
    for connection in connections.values():
        connection.close()

    # write output
    if write_dict is not None:
        with open(write_dict, "w") as f:
            f.write(json.dumps(objects))

    return objects


if __name__ == "__main__":
    print(json.dumps(fetch_details()))
