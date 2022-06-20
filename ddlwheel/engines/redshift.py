"""`Redshift` facilities."""

import typing

from redshift_connector import Connection, connect
from redshift_connector.cursor import Cursor
from tqdm import tqdm

from ..parsers.common import clean_query, fetch_children, fetch_parents
from . import Engine


class Redshift(Engine):
    """`Redshift` client object."""

    def __init__(self, **connection_kwargs):
        """Set up the connection parameters and class objects.

        Parameters
        ----------
        connection_kwargs : dict[str, int | str]
            Connection parameters to connect to the `Redshift` database.

        Attributes
        ----------
        config : dict[str, int | str]
            Connection parameters to connect to the `Redshift` database.
        connections : dict[str, redshift_connector.Connection]
            Dictionary of connection objects for each database encountered.
        objects : dict[str, typing.Any]
            Dictionary of objects encountered, indexed by their respective long names.
        """
        self.config = {
            "user": connection_kwargs.get("user"),
            "password": connection_kwargs.get("password"),
            "host": connection_kwargs.get("host"),
            "port": connection_kwargs.get("port", 5439),
            "database": connection_kwargs.get("database"),
        }

        self.connections: dict[str, Connection] = {}
        self.objects: dict[str, typing.Any] = {}

    @staticmethod
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
            Dictionary describing the object columns (name, datatypes).

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

        return [{"name": n, "datatype": t} for n, t in c]

    @staticmethod
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
            One of `external table`, `procedure`, `table` or `view` (last one accounting
            for materialized views as well).

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
            cursor.execute(f"show {t} {d}.{s}.{n}")
            return cursor.fetchone()[0]
        except Exception:
            return "-- UNABLE TO FETCH"

    def fetch(self):
        """List all objects in all databases and fetch all information for each."""
        # fetching the list of all objects does not require a particular database
        with connect(**self.config) as connection:
            with connection.cursor() as cursor:
                self.fetch_objects(cursor)

        # fetching the list of all stored procedures *does* require a particular
        # database the next few lines clobber existing objects in the database
        for d in self.connections:
            with self.connections[d].cursor() as cursor:
                self.fetch_procs(cursor, d)

        self.objects = dict(sorted(self.objects.items()))
        paths = list(self.objects.keys())

        # loop over each object and fetch its ddl and columns details, and extract
        # parents and children from the former
        for i, o in enumerate(tqdm(self.objects, desc="Fetch object details")):
            n = self.objects[o]["name"]
            s = self.objects[o]["schema"]
            d = self.objects[o]["database"]
            t = self.objects[o]["type"]

            with self.connections[d].cursor() as cursor:
                f = self.fetch_ddl(cursor, n, s, d, t)
                q = clean_query(f)  # clean the query

                # parent details
                p = fetch_parents(q, paths, d)

                # column details
                if t == "PROCEDURE":
                    c = []
                    k = fetch_children(q, paths, d)
                else:
                    c = self.fetch_columns(cursor, n, s, d)
                    k = []

                self.objects[o].update(
                    {"ddl": f, "columns": c, "parents": p, "children": k}
                )

        # close all created connections
        for connection in self.connections.values():
            connection.close()

    def fetch_objects(self, cursor: Cursor):
        """List all objects in all `Redshift` databases.

        Parameters
        ----------
        cursor : redshift_connector.cursor.Cursor
            Cursor to use to run the query.

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
            if d not in self.connections:
                config = self.config.copy()
                config.update({"database": d})
                self.connections[d] = connect(**config)

            # save the object
            self.objects[f"{d}.{s}.{n}"] = {
                "name": n,
                "schema": s,
                "database": d,
                "type": t,
            }

    def fetch_procs(self, cursor: Cursor, d: str):
        """List all stored procedures in all schemas of a `Redshift` database.

        Parameters
        ----------
        cursor : redshift_connector.cursor.Cursor
            Cursor to use to run the query.
        d : str
            Name of the database hosting the schema.

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
            self.objects[f"{d}.{s}.{n}"] = {
                "name": n,
                "schema": s,
                "database": d,
                "type": t,
            }
