"""Template object for flavoured clients; act as documentation."""

import json
import typing


class Engine:
    """Metaclass documenting the necessary minimal implementation."""

    def __init__(self, **connection_kwargs):
        """Set up the connection parameters and class objects.

        Parameters
        ----------
        connection_kwargs : dict[str, int | str]
            Connection parameters to connect to the given database.

        Attributes
        ----------
        config : dict[str, int | str]
            Connection parameters to connect to the given database.
        connections : dict[str, object]
            Dictionary of connection objects (type specific to the database client) for
            each database encountered.
        objects : dict[str, typing.Any]
            Dictionary of objects encountered, indexed by their respective long names.
        """
        self.config = {
            "user": connection_kwargs.get("username"),
            "password": connection_kwargs.get("password"),
            "host": connection_kwargs.get("hostname", "localhost"),
            "port": connection_kwargs.get("port", 5432),
            "db": connection_kwargs.get("database", "default"),
        }

        self.connections: dict[str, object] = {}
        self.objects: dict[str, typing.Any] = {}

    @staticmethod
    def fetch_ddl(cursor, *args, **kwargs) -> str:
        """Fetch the DDL of an object.

        Parameters
        ----------
        cursor
            Cursor (object type specific to the database client) to use to run the
            query.

        Returns
        -------
        : str
            DDL of the object.
        """
        raise NotImplementedError

    @staticmethod
    def fetch_columns(cursor, *args, **kwargs) -> list[dict[str, str]]:
        """List all columns from an object.

        Parameters
        ----------
        cursor : redshift_connector.cursor.Cursor
            Cursor (object type specific to the database client) to use to run the
            query.

        Returns
        -------
        : list[dict[str, str]]
            Dictionary describing the object columns (name, datatypes).
        """
        raise NotImplementedError

    def fetch(self):
        """List all objects in all databases and fetch all information for each."""
        raise NotImplementedError

    def fetch_objects(self, cursor):
        """List all objects in all accessible databases.

        This method should also generate connection objects (type specific to the
        database client) for each accessible database; stored in the `connections`
        dictionary.

        Parameters
        ----------
        cursor
            Cursor (object type specific to the database client) to use to run the
            query.
        """
        raise NotImplementedError

    def dump_objects(self, path="objects.json"):
        """Dump the `objects` dictionary in JSON format to the given path.

        Parameters
        ----------
        path : str
            Write the `objects` dictionary in JSON format to that path.
        """
        with open(path, "w") as f:
            f.write(json.dumps(self.objects))
