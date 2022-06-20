"""Facilities to generate input for the wheel."""

import re
import typing


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
