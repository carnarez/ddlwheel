"""Common tools, parsers and helpers."""

import re
import typing

from sqlparse import format as sqlformat


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


def _cname(path: str, name: str) -> str:
    """Return the canonical name of an object, inferred from its path.

    Parameters
    ----------
    path : str
        Path of the object considered.
    name : str
        Long name of the object considered.

    Returns
    -------
    : str
        Canonical name of the object.
    """
    # s3, or temporary objects (latter ignored)
    if path == ".":
        if name.startswith("s3"):
            return ".".join(re.sub("s3.*://", "s3/", name).split("/")[:3])

    # database object
    else:
        return path.strip(".")

    return ""


def family_tree(objects: dict[str, typing.Any]) -> list[dict[str, list[str] | str]]:
    """Identify imports of an object.

    Parameters
    ----------
    objects : dict[str, typing.Any]
        Dictionary of objects encountered, indexed by their respective long names.

    Returns
    -------
    : list[dict[str, list[str] | str]]
        List of dictionary of name and parents/children lists.
    """
    tree: list[dict[str, list[str] | str]] = []

    incoming: dict[str, list[str]] = {o: [] for o in objects.keys()}
    outgoing: dict[str, list[str]] = {o: [] for o in objects.keys()}

    external: list[str] = []

    for oi in objects.keys():

        # parents
        if objects[oi]["parents"] is not None:
            for p in objects[oi]["parents"]:
                if (oj := _cname(p["path"], p["name"])) != "":
                    incoming[oi].append(oj)

                    try:
                        outgoing[oj].append(oi)
                    except KeyError:
                        outgoing[oj] = [oi]

                        # fix for objects *outside* the database itself
                        incoming[oj] = []
                        external.append(oj)

        # children
        if objects[oi]["children"] is not None:
            for k in objects[oi]["children"]:
                if (oj := _cname(k["path"], k["name"])) != "":
                    outgoing[oi].append(oj)

                    try:
                        incoming[oj].append(oi)
                    except KeyError:
                        incoming[oj] = [oi]

    for o in list(objects.keys()) + external:
        d = objects.get(o, {}).get("database", "s3")
        s = objects.get(o, {}).get("schema", "s3")

        # rework of some object path and type for visualization
        if d == "s3":
            if "preprod" in o:
                d = "s3-preprod"
            s = o.split(".")[1]
            t = "BUCKET"
        else:
            t = objects[o]["type"]
            if t == "PROCEDURE":
                t = "STORED PROCEDURE"
            if t == "VIEW" and re.match(
                r"create\s+materialized\s+view", objects[o]["ddl"].lower()
            ):
                t = "MATERIALIZED VIEW"

        tree.append(
            {
                "database": d,
                "schema": s,
                "name": o,
                "incoming": [i for i in incoming[o]],
                "outgoing": [o for o in outgoing[o]],
                "type": t,
            }
        )

    return sorted(tree, key=lambda o: o["name"].lower())  # type: ignore


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
