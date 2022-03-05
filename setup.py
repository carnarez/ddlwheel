"""Make `ddltree` installable (via `pip install git+https://...`)."""

import setuptools  # type: ignore

setuptools.setup(
    author="carnarez",
    description="Parse a SQL DDL and extract column lineage.",
    install_requires=["sqlparse"],
    name="ddltree",
    packages=["ddltree"],
    package_data={"ddltree": ["py.typed"]},
    url="https://github.com/carnarez/ddltree",
    version="0.0.1",
)
