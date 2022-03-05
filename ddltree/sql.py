"""Parse a SQL script and extract aliases, column and table lineage/dependencies.

Usage
-----
```shell
$ python sql.py [SCRIPT.sql [SCRIPT.sql [...]]]
```
"""

import json
import re
import sys
import traceback
import typing

import sqlfluff
import sqlparse


class Feature:
    """Describe a column."""

    def __init__(self, **kwargs):
        """Initiate the object.

        Attributes
        ----------
        """
        self.kind: str = ""
        self.alias: str = ""
        self.path: str = ""
        self.trans: str = ""
        self.trans_ident: list[str] = []

        self._depth: int = 0
        self._text: str = ""

        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def __repr__(self):
        """Define a pallatable output."""
        s = f"{self._depth:2d} {self.kind}="

        if len(self.alias):
            s += f"{self.alias}"
        else:
            s += f"{self._text}"

        if len(self.path) and self.path != self.alias:
            s += f" ({self.path})"

        if len(self.trans):
            s += f' trans="{self.trans}"'

        if len(self.trans_ident):
            s += f' via=[ {", ".join(self.trans_ident)} ]'

        return s


class Collection:
    """Describe a table or a view."""

    def __init__(self, features: list[Feature]):
        """Initiate the object.

        Attributes
        ----------
        """
        self.features: list[Feature] = features


def _clean_dialect(q: str) -> str:
    """Some ad-hoc changes that should not impact the end goal.

    Parameters
    ----------
    q : str
        The SQL query.

    Returns
    -------
    : str
        Cleaned up query.

    Note
    ----
    Function applying filters specific to
    [`Redshift`](https://docs.aws.amazon.com/redshift/latest/dg/welcome.html).
    """
    # ad-hoc change for sqlfluff (they should not impact the meaning of the scripts)
    q = re.sub("BACKUP NO", "", q, flags=re.IGNORECASE)
    q = re.sub("DISTKEY\s*\(.*", "", q, flags=re.IGNORECASE)
    q = re.sub("DISTSTYLE KEY", "", q, flags=re.IGNORECASE)
    q = re.sub("EXTERNAL", "", q, flags=re.IGNORECASE)
    q = re.sub("LOCATION\s*'s3.*", "", q, flags=re.IGNORECASE)
    q = re.sub("MATERIALIZED VIEW", "TABLE", q, flags=re.IGNORECASE)
    q = re.sub("OUTPUTFORMAT\s*'org.*", "", q, flags=re.IGNORECASE)
    q = re.sub("PARTITIONED BY.*", "", q, flags=re.IGNORECASE)
    q = re.sub("ROW FORMAT SERDE.*", "", q, flags=re.IGNORECASE)
    q = re.sub("STORED AS.*", "", q, flags=re.IGNORECASE)
    q = re.sub("SORTKEY\s*\(.*", "", q, flags=re.IGNORECASE)
    q = re.sub("WITH NO SCHEMA BINDING", "", q, flags=re.IGNORECASE)

    return q


def clean_query(q: str) -> str:
    """Deep-cleaning of the SQL query.

    Parameters
    ----------
    q : str
        The SQL query.

    Returns
    -------
    : str
        Cleaned up query.
    """
    # good effort, but does not know some functions/keywords
    q = sqlparse.format(q, keyword_case="lower", strip_comments=True)

    # regular cleaning
    q = re.sub(r"/\*.*\*/", "", q, flags=re.DOTALL)
    q = re.sub(r"--.*", "", q)
    q = re.sub("([(,)])", r" \1 ", q)
    q = re.sub(r"([A-Za-z0-9_]+)\s*\.\s*([A-Za-z0-9_]+)", r"\1.\2", q)
    q = re.sub(r"(.*)\s*=\s*(.*)", r"\1=\2", q)
    q = re.sub(r"(.*)\s*\|\|\s*(.*)", r"\1 || \2", q)
    q = re.sub(r"(.*)\s*::\s*(.*)", r"\1::\2", q)
    q = re.sub(r"[\s]+", " ", q).strip()

    return q


def parse_query(q: str) -> dict[str, dict[str, dict[str, str]]]:
    """Parse query to extract schemas, table/views and columns; with aliases.

    Parameters
    ----------
    q : str
        The SQL query.

    Returns
    -------
    : dict[str, dict[str, dict[str, str]]]
        Dictionary of schemas, table/views (including emporary objects) and columns
        (including aliases).
    """
    try:
        ast = sqlfluff.parse(q, dialect="redshift")["file"]["statement"]
        return through_ast(ast)
    except Exception as e:
        s = "-" * 40
        print(f"{s}{s}\n{q}\n{s}\n{traceback.format_exc(e)}")


def _flatten_nested_json(
    d: dict[str, typing.Any], l: list[Feature] = [], depth: int = 0
) -> list[Feature]:
    """Traverse the AST and flatten it.

    Parameters
    ----------
    d : dict[str, typing.Any]
        The Abstract Syntax Tree of the query as parsed by `sqlfluff.parse()`.
    l : list[Feature]
        Current list of features.
    depth : int
        The nesting depth of the feature. Starts at 0.

    Returns
    -------
    : list[Feature]
        Flattened and cleaned up list of features.
    """
    for k, v in d.items():
        if k not in ("whitespace", "new_line"):  # more?
            if type(v) == dict:
                _flatten_nested_json(v, l, depth + 1)
            elif type(v) in (list, tuple):
                for nv in v:
                    if type(nv) == dict:
                        _flatten_nested_json(nv, l, depth + 1)
            else:
                l.append(Feature(kind=k, _depth=depth, _text=v))

    return l


def _join_identifiers(l: list[Feature]) -> list[Feature]:
    """Join schema/table/alias to table/view/column.

    Parameters
    ----------
    features : list[Feature]
        List of features.

    Returns
    -------
    : list[Feature]
        Cleaned up list of features.
    """
    for i in range(len(l) - 2):
        if l[i].kind is None:
            continue

        # check what comes next...
        # the alias is the same as the path (for now)
        if (l[i].kind, l[i + 1].kind, l[i + 2].kind) == ("identifier", "dot", "identifier"):
            s = f"{l[i]._text}.{l[i + 2]._text}"
            l[i].path = s
            l[i].alias = s
            l[i]._text = s
            l[i + 1].kind = None
            l[i + 2].kind = None

    return l


def _fetch_case(l: list[Feature]) -> list[Feature]:
    """Fetch and format the `CASE WHEN (...) END` transformations.

    Parameters
    ----------
    features : list[Feature]
        List of features.

    Returns
    -------
    : list[Feature]
        Cleaned up list of features.
    """
    for i in range(len(l) - 1):
        if l[i].kind is None:
            continue

        if (l[i].kind, l[i]._text.lower()) == ("keyword", "case"):
            l[i].kind = "identifier"
            l[i].path = l[i]._text

            trans: list[str] = ["case"]
            trans_ident: list[str] = []

            # skip until finding the end statement
            # store content on the way, and empty as well
            for j in range(i + 1, len(l) - i - 2):
                trans.append(l[j]._text)
                if l[j].kind == "identifier" and l[j]._text not in trans_ident:
                    trans_ident.append(l[j]._text)

                l[j].kind = None

                if (l[j]._depth, l[j]._text.lower()) == (l[i]._depth, "end"):
                    break

            # store the transformation and involved column
            l[i].trans = " ".join(trans)
            l[i].trans_ident = trans_ident

    return l


def _fetch_func(l: list[Feature]) -> list[Feature]:
    """Fetch and format the `FUNCTION(...)` transformations.


    Parameters
    ----------
    features : list[Feature]
        List of features.

    Returns
    -------
    : list[Feature]
        Cleaned up list of features.
    """
    for i in range(len(l) - 1):
        if l[i].kind is None:
            continue

        if (l[i].kind, l[i + 1].kind) == ("function_name_identifier", "start_bracket"):
            l[i].kind = "identifier"
            l[i].path = l[i]._text

            trans: list[str] = [l[i]._text]
            trans_ident: list[str] = []

            # skip until finding the end statement
            # store content on the way, and empty as well
            for j in range(i + 1, len(l) - i - 2):
                trans.append(l[j]._text)
                if l[j].kind == "identifier" and l[j]._text not in trans_ident:
                    trans_ident.append(l[j]._text)

                k = l[j].kind
                l[j].kind = None

                if (l[j]._depth, k) == (l[i]._depth, "end_bracket"):
                    break

            # store the transformation and involved column
            l[i].trans = " ".join(trans)
            l[i].trans_ident = trans_ident

    return l


def _clean_list(l: list[Feature]) -> list[Feature]:
    """Remove all features filled with `None`s.

    Parameters
    ----------
    features : list[Feature]
        List of features.

    Returns
    -------
    : list[Feature]
        Cleaned up list of features.
    """
    return [f for f in l if f.kind is not None]


def _fetch_alias(l: list[Feature]) -> list[Feature]:
    """Fetch/update object and column aliases.

    Parameters
    ----------
    features : list[Feature]
        List of features.

    Returns
    -------
    : list[Feature]
        Cleaned up list of features.
    """
    for i in range(len(l) - 2):
        if l[i].kind is None:
            continue

        # fetch [schema.]object alias, if existing
        if (l[i].kind, l[i + 1].kind) == ("identifier", "identifier"):
            l[i].alias = l[i + 1]._text
            l[i + 1].kind = None

        # fetch column alias, if existing
        if (l[i].kind, l[i + 1].kind, l[i + 1]._text.lower(), l[i + 2].kind) == ("identifier", "keyword", "as", "identifier"):
            l[i].alias = l[i + 2]._text
            l[i + 1].kind = None
            l[i + 2].kind = None

    return l


def through_ast(ast: dict[str, typing.Any]) -> dict[str, dict[str, dict[str, str]]]:
    """Refine what we need by cleaning up/reformating the flattened AST.

    Parameters
    ----------
    ast : dict[str, typing.Any]
        The Abstract Syntax Tree of the query as parsed by `sqlfluff.parse()`.

    Returns
    -------
    : dict[str, dict[str, dict[str, str]]]
        Dictionary of schemas, tables/views (including temporary objects) and columns.
    """
    # nested json ast to list of feature objects
    l = _flatten_nested_json(ast)

    # iteratively compress the object paths
    nr = len(l)
    prev_nr = 0
    while nr != prev_nr:
        l = _join_identifiers(l)
        l = _clean_list(l)
        prev_nr = nr
        nr = len(l)

    # compress the transformations
    l = _fetch_case(l)
    l = _fetch_func(l)
    l = _clean_list(l)

    # fetch the aliases
    l = _fetch_alias(l)
    l = _clean_list(l)

    for f in l:
        print(f)


if __name__ == "__main__":
    qs: list[str] = []

    # read each query in each file
    for a in sys.argv[1:]:
        with open(a) as f:
            for q in sqlparse.split(f.read()):
                q = _clean_dialect(q)
                q = clean_query(q)
                if len(q):
                    qs.append(q)

    # parse each query
    for q in qs:
        parse_query(q)
