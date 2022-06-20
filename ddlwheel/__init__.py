# flake8: noqa
# isort: skip_file

"""Extract information of SQL objects from a database.

Usage
-----
Below an example for `Redshift`:

```python
from ddlwheel import Redshift

r = Redshift(
    user=os.environ["REDSHIFT_USER"],
    password=os.environ["REDSHIFT_PASSWORD"],
    host=os.environ["REDSHIFT_HOST"],
    port=int(os.environ.get("REDSHIFT_PORT", 5439)),
    database=os.environ["REDSHIFT_DB"],
)

r.fetch()
r.dump_objects("objects.json")
```

To generate the format expected by the `d3.js` script process the data further:

```
from wheel import family_tree

with open("data.json", "w") as f:
    f.write(json.dumps(family_tree(r.objects)))
```
"""

from .engines.redshift import Redshift

__version__: str = "0.0.1"
