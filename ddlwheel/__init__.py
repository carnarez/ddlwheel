"""Extract and visualise a dependency wheel of SQL objects.

Usage
-----
Below an example for `Redshift`:
```python
from common import fetch_family
from engines.redshift import fetch_details

objects = fetch_details()
tree = fetch_family(objects)

with open("objects.json", "w") as f:
    f.write(json.dumps(objects))  # to reuse at a later date

with open("family_tree.json", "w") as f:
    f.write(json.dumps(tree))  # format expected by the d3 script
```
"""

__version__: str = "0.0.1"
