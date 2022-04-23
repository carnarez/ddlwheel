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


def fetch_family(objects: dict[str, typing.Any]) -> list[dict[str, list[str] | str]]:
    """Identify direct family tree of an object (parents and descendants).

    Parameters
    ----------
    objects : dict[str, typing.Any]
        Dictionary of objects encountered, indexed by their respective long names.

    Returns
    -------
    : list[dict[str, list[str] | str]]
        List of dictionary of name and parents/children lists.
    """
    external: list[str] = []
    incoming: dict[str, list[str]] = {o: [] for o in objects.keys()}
    outgoing: dict[str, list[str]] = {o: [] for o in objects.keys()}

    for oi in objects.keys():
        for oj in objects[oi]["parents"]:
            if oj is not None:
                incoming[oi].append(oj)

                try:
                    outgoing[oj].append(oi)
                except KeyError:
                    outgoing[oj] = [oi]

                    # fix for objects *outside* the database itself
                    incoming[oj] = []
                    external.append(oj)

    tree = [
        {
            "name": o,
            "incoming": [i for i in incoming[o]],
            "outgoing": [o for o in outgoing[o]],
        }
        for o in list(objects.keys()) + external
    ]

    return sorted(tree, key=lambda o: o["name"].lower())


def fetch_parents(query: str, paths: list[str], database: str) -> list[dict[str, str]]:
    """Extract objects from `FROM`/`JOIN`/`LOCATION` statements. Skip temporary ones.

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
        List of objects encountered in `FROM ...`, `JOIN ...` or `LOCATION ...`
        statements.
    """
    l: list[str] = []
    p: list[dict[str, str]] = []

    def _match(name: str) -> str:
        """Match a short name to the most probable object.

        Parameters
        ----------
        name : str
            Object to identify.

        Returns
        -------
        : str
            Full path to the identified object.

        Note
        ----
        Stateful hidden function!
        """
        for p in paths:

            # database.schema.object
            if name.count(".") == 2 and p == name:
                return p

            # schema.object
            # object
            if p.startswith(f"{database}.") and p.endswith(name):
                return p

        return None

    # parent objects
    for m in re.finditer(r"from\s+([^(].*?)[(\s;)]", query, flags=re.IGNORECASE):
        if (o := m.group(1)) not in l and o not in p:
            p.append({"name": o, "path": _match(o)})
            l.append(o)  # abusing this list for bookkeeping

    # joined objects
    for m in re.finditer(r"join\s+([^(].*?)[(\s)]", query, flags=re.IGNORECASE):
        if (o := m.group(1)) not in l and o not in p:
            p.append({"name": o, "path": _match(o)})
            l.append(o)

    # redshift (aws-flavoured postgres): s3-located data queried/indexed in glue via
    # athena
    for m in re.finditer(r"location\s+'(.*)'", query, flags=re.IGNORECASE):
        if (o := m.group(1)) not in l and o not in p:
            p.append({"name": o, "path": None})
            l.append(o)

    return sorted(p, key=lambda o: o["name"])
