"""Make `ddlwheel` installable (via `pip install git+https://...`)."""

import setuptools  # type: ignore

setuptools.setup(
    author="carnarez",
    description="Query and parse SQL DDL, and extract lineage.",
    install_requires=["sqlparse", "tqdm"],
    name="ddlwheel",
    packages=setuptools.find_packages(),
    package_data={"ddlwheel": ["py.typed"]},
    url="https://github.com/carnarez/ddlwheel",
    version="0.0.1",
)
