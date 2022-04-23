# Module `ddlwheel`

Extract and visualise a dependency wheel of SQL objects.

**Usage**

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

# Module `ddlwheel.engines`

Database-flavoured utils and functions.

In particular, three functions are expected in each engine module:

- `fetch_objects()` listing all database objects to describe.
- `fetch_ddl()` querying the definition of a single object (DDL) which will later be
  parsed to extract direct parents.
- `fetch_details()` which does all the work, that is, leverages the previous functions
  to "fully" describe all objects in the database(s).

# Module `ddlwheel.engines.redshift`

`Redshift` facilities.

**Functions**

- [`fetch_objects()`](#ddlwheelenginesredshiftfetch_objects): List all objects in all
  `Redshift` databases.
- [`fetch_ddl()`](#ddlwheelenginesredshiftfetch_ddl): Fetch the DDL of an object.
- [`fetch_columns()`](#ddlwheelenginesredshiftfetch_columns): List all columns from an
  object.
- [`fetch_details()`](#ddlwheelenginesredshiftfetch_details): List all objects in all
  databases and fetch their respective DDLs and columns.

## Functions

### `ddlwheel.engines.redshift.fetch_objects`

```python
fetch_objects(cursor: Cursor, objects: dict) -> tuple:
```

List all objects in all `Redshift` databases.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.
- `objects` \[`dict[str, typing.Any]`\]: Empty dictionary of objets encountered.

**Returns**

- \[`dict[str, redshift_connector.connection.Connection]`\]: Dictionary of connection
  object for each database encountered.
- \[`dict[str, typing.Any]`\]: Dictionary of objects encountered, indexed by their
  respective long names.

**Notes**

Performing the following query:

```sql
select
    database_name,
    schema_name,
    table_name,
    table_type
from
    pg_catalog.svv_all_tables
where
    schema_name not in ('information_schema', 'pg_catalog')
    and substring(table_name, 1, 8) <> 'mv_tbl__'
order by
    database_name, schema_name, table_name
```

### `ddlwheel.engines.redshift.fetch_ddl`

```python
fetch_ddl(cursor: Cursor, n: str, s: str, d: str, t: str) -> str:
```

Fetch the DDL of an object.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.
- `n` \[`str`\]: Name of the object.
- `s` \[`str`\]: Name of the schema hosting the object.
- `d` \[`str`\]: Name of the database hosting the schema.
- `t` \[`str`\]: One of `external table`, `table` or `view` (last one accounting for
  materialized views as well).

**Returns**

- \[`str`\]: DDL of the object.

**Notes**

Performing the following \[example\] query:

```sql
show external table schema.table
```

### `ddlwheel.engines.redshift.fetch_columns`

```python
fetch_columns(cursor: Cursor, n: str, s: str, d: str) -> list:
```

List all columns from an object.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.
- `n` \[`str`\]: Name of the object.
- `s` \[`str`\]: Name of the schema hosting the object.
- `d` \[`str`\]: Name of the database hosting the schema.

**Returns**

- \[`list[dict[str, str]]`\]: Dictionary describing the object columns (name and
  datatypes).

**Notes**

Performing the following \[example\] query:

```sql
select
    column_name,
    data_type
from
    pg_catalog.svv_all_columns
where
    database_name = 'database'
    and schema_name = 'schema'
    and table_name = 'table'
order by
    ordinal_position
```

### `ddlwheel.engines.redshift.fetch_details`

```python
fetch_details() -> dict:
```

List all objects in all databases and fetch their respective DDLs and columns.

**Returns**

- \[`dict[str, typing.Any]`\]: Dictionary of objects encountered, indexed by their
  respective long names.

# Module `ddlwheel.utils`

Common tools, parsers and helpers.

**Functions**

- [`clean_query()`](#ddlwheelutilsclean_query): Deep-cleaning of a SQL query.
- [`fetch_family()`](#ddlwheelutilsfetch_family): Identify direct family tree of an
  object (parents and descendants).
- [`fetch_parents()`](#ddlwheelutilsfetch_parents): Extract objects from
  `FROM`/`JOIN`/`LOCATION` statements. Skip temporary ones.

## Functions

### `ddlwheel.utils.clean_query`

```python
clean_query(query: str) -> str:
```

Deep-cleaning of a SQL query.

**Parameters**

- `query` \[`str`\]: The SQL query.

**Returns**

- \[`str`\]: Cleaned up query.

### `ddlwheel.utils.fetch_family`

```python
fetch_family(objects: dict) -> list:
```

Identify direct family tree of an object (parents and descendants).

**Parameters**

- `objects` \[`dict[str, typing.Any]`\]: Dictionary of objects encountered, indexed by
  their respective long names.

**Returns**

- \[`list[dict[str, list[str] | str]]`\]: List of dictionary of name and
  parents/children lists.

### `ddlwheel.utils.fetch_parents`

```python
fetch_parents(query: str, paths: list, database: str) -> list:
```

Extract objects from `FROM`/`JOIN`/`LOCATION` statements. Skip temporary ones.

**Parameters**

- `query` \[`str`\]: The DDL to parse.
- `paths` \[`list[str]`\]: List of object full paths.
- `database` \[`str`\]: Limit the matching to a specific database.

**Returns**

- \[`list[dict[str, str]]`\]: List of objects encountered in `FROM ...`, `JOIN ...` or
  `LOCATION ...` statements.
