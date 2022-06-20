"""Common tools, parsers and helpers."""

import re

from sqlparse import format as sqlformat


def _match(name: str, paths: list[str], database: str) -> str:
    """Match a short name to the most probable object.

    Parameters
    ----------
    name : str
        The short name to consider.
    paths : list[str]
        List of object full paths.
    database : str
        Limit the matching to a specific database.

    Returns
    -------
    : str
        Most probable object long name associated with a short name.
    """
    for p in paths:

        # database.schema.object
        if name.count(".") == 2 and p == name:
            return p

        # schema.object or object
        if p.startswith(f"{database}.") and p.endswith(name):
            return p

    return ""


def clean_query(query: str) -> str:
    """Deep-cleaning of a SQL query.

    Parameters
    ----------
    query : str
        The SQL query.

    Returns
    -------
    : str
        Cleaned up query.
    """
    # good effort, but does not know some functions/keywords
    q = sqlformat(query, keyword_case="upper", strip_comments=True)

    # regular cleaning
    q = re.sub(r"/\*.*\*/", "", q, flags=re.DOTALL)
    q = re.sub(r"--.*", "", q)
    q = re.sub("([(,)])", r" \1 ", q)
    q = re.sub(r"([A-Za-z0-9_]+)\s*\.\s*([A-Za-z0-9_]+)", r"\1.\2", q)
    q = re.sub(r"(.*)\s*=\s*(.*)", r"\1 = \2", q)
    q = re.sub(r"(.*)\s*\|\|\s*(.*)", r"\1 || \2", q)
    q = re.sub(r"(.*)\s*::\s*(.*)", r"\1::\2", q)
    q = re.sub(r"[\s]+", " ", q).strip()

    return q


def fetch_children(query: str, paths: list[str], database: str) -> list[dict[str, str]]:
    r"""Extract objects from various SQL statements. Skip temporary ones.

    Parameters
    ----------
    query : str
        The DDL to parse.
    paths : list[str]
        List of object full paths.
    database : str
        Limit the matching to a specific database.

    Returns
    -------
    : list[dict[str, str]]
        List of permanent objects encountered in various SQL statements (see below).

    Notes
    -----
    Regexes:
    * `ALTER MATERIALIZED VIEW\s+([^(].*?)\s`
    * `ALTER TABLE\s+([^(].*?)\s`
    * `CREATE\s+.*\s+MATERIALIZED VIEW\s+([^(].*?)\s`
    * `CREATE\s+.*\s+TABLE IF NOT EXISTS\s+([^(].*?)\s`
    * `CREATE\s+.*\s+TABLE\s+([^(].*?)\s`
    * `CREATE\s+.*\s+VIEW\s+([^(].*?)\s`
    * `INSERT INTO\s+([^(].*?)\s`
    * `REFRESH MATERIALIZED VIEW\s+([^(].*?)\s`
    * `SELECT\s+.*\s+INTO\s+([^(].*?)\s`
    * `UPDATE\s+([^(].*?)\s`
    """
    l: list[str] = []
    k: list[dict[str, str]] = []  # kids

    for r in (
        # alter materialized view or table
        r"ALTER MATERIALIZED VIEW\s+([^(].*?)\s",
        r"ALTER TABLE\s+([^(].*?)\s",
        # create materialized view, table or view
        r"CREATE\s+.*\s+MATERIALIZED VIEW\s+([^(].*?)\s",
        r"CREATE\s+.*\s+TABLE IF NOT EXISTS\s+([^(].*?)\s",
        r"CREATE\s+.*\s+TABLE\s+([^(].*?)\s",
        r"CREATE\s+.*\s+VIEW\s+([^(].*?)\s",
        # insert into
        r"INSERT INTO\s+([^(].*?)\s",
        # refresh
        r"REFRESH MATERIALIZED VIEW\s+([^(].*?)\s",
        # select into; no support for extra keywords!
        r"SELECT\s+.*\s+INTO\s+([^(].*?)\s",
        # update
        r"UPDATE\s+([^(].*?)\s",
    ):

        # some keywords are not recognized by sqlparse and not uppercased
        if "materialized" in r.lower():
            f = re.IGNORECASE
        else:
            f = 0  # type: ignore

        for m in re.finditer(r, query, flags=f):
            if (o := m.group(1)) not in l:
                k.append({"name": o, "path": f".{_match(o, paths, database)}"})
                l.append(o)  # bookkeeping

    return sorted(k, key=lambda o: o["name"])


def fetch_parents(query: str, paths: list[str], database: str) -> list[dict[str, str]]:
    r"""Extract objects from `FROM`/`JOIN`/`LOCATION` statements. Skip temporary ones.

    Parameters
    ----------
    query : str
        The DDL to parse.
    paths : list[str]
        List of object full paths.
    database : str
        Limit the matching to a specific database.

    Returns
    -------
    : list[dict[str, str]]
        List of permanent objects encountered in `FROM ...`, `JOIN ...` or
        `LOCATION ...` statements.

    Notes
    -----
    Regexes:
    * `FROM\s+([^(].*?)[(\s;)]`
    * `JOIN\s+([^(].*?)[(\s)]`
    * `LOCATION\s+'(.*)'`
    """
    l: list[str] = []
    p: list[dict[str, str]] = []  # parents

    for r in (
        r"FROM\s+([^(].*?)[(\s;)]",
        r"JOIN\s+([^(].*?)[(\s)]",
        r"LOCATION\s+'(.*)'",
    ):
        for m in re.finditer(r, query):
            if (o := m.group(1)) not in l:
                p.append({"name": o, "path": f".{_match(o, paths, database)}"})
                l.append(o)  # bookkeeping

    return sorted(p, key=lambda o: o["name"])
