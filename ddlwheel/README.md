# Module `__init__`

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

# Module `engines`

Database-flavoured utils and functions.

In particular, three functions are expected in each engine module:

- `fetch_objects()` listing all database objects to describe.
- `fetch_ddl()` querying the definition of a single object (DDL) which will later be
  parsed to extract direct parents.
- `fetch_details()` which does all the work, that is, leverages the previous functions
  to "fully" describe all objects in the database(s).

# Module `engines.redshift`

`Redshift` facilities.

**Functions**

- [`fetch_objects()`](#enginesredshiftfetch_objects): List all objects in all `Redshift`
  databases.
- [`fetch_procs()`](#enginesredshiftfetch_procs): List all stored procedures in all
  schemas of a `Redshift` database.
- [`fetch_ddl()`](#enginesredshiftfetch_ddl): Fetch the DDL of an object.
- [`fetch_columns()`](#enginesredshiftfetch_columns): List all columns from an object
  and sample associated data.
- [`fetch_details()`](#enginesredshiftfetch_details): List all objects in the database,
  fetch their DDLs and sample their data.

## Functions

### `engines.redshift.fetch_objects`

```python
fetch_objects(
    cursor: Cursor,
    objects: dict[str, typing.Any] = {},
) -> tuple[dict[str, Connection], dict[str, typing.Any]]:
```

List all objects in all `Redshift` databases.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.
- `objects` \[`dict[str, str]`\]: Empty dictionary of objets encountered.

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
    table_name as object_name,
    table_type as object_type
from
    pg_catalog.svv_all_tables
where
    schema_name not in ('information_schema', 'pg_catalog')
    and substring(table_name, 1, 8) <> 'mv_tbl__'
order by
    database_name, schema_name, table_name
```

### `engines.redshift.fetch_procs`

```python
fetch_procs(
    cursor: Cursor,
    d: str,
    procs: dict[str, typing.Any] = {},
) -> dict[str, typing.Any]:
```

List all stored procedures in all schemas of a `Redshift` database.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.
- `d` \[`str`\]: Name of the database hosting the schema.
- `procs` \[`dict[str, typing.Any]`\]: Empty dictionary of procedures encountered.

**Returns**

- \[`dict[str, typing.Any]`\]: Dictionary of procedures encountered, indexed by their
  respective long names.

**Notes**

Performing the following query:

```sql
select
    'database' as database_name,
    n.nspname as schema_name,
    p.proname as object_name,
    'PROCEDURE' as object_type
from
    pg_catalog.pg_namespace n
join
    pg_catalog.pg_proc p
on
    pronamespace = n.oid
where
    proowner = current_user_id
    and proname <> 'get_result_set'
```

### `engines.redshift.fetch_ddl`

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

### `engines.redshift.fetch_columns`

```python
fetch_columns(
    cursor: Cursor,
    n: str,
    s: str,
    d: str,
    root_dir: str,
) -> list[dict[str, str]]:
```

List all columns from an object and sample associated data.

If a `sample.sql` file is found in the given directory it is used to sample the various
columns of the object. Do NOT make it random! Otherwise each time this script will run a
new `README.md` will have to be committed.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.
- `n` \[`str`\]: Name of the object.
- `s` \[`str`\]: Name of the schema hosting the object.
- `d` \[`str`\]: Name of the database hosting the schema.
- `root_dir` \[`str`\]: Directory in which to write content/fetch content from.

**Returns**

- \[`list[dict[str, str]]`\]: Dictionary describing the object columns (name, datatypes,
  samples if a `sample.sql` is provided).

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

### `engines.redshift.fetch_details`

```python
fetch_details(
    root_dir: str = "./",
    write_dict: str = "objects.json",
) -> dict[str, typing.Any]:
```

List all objects in the database, fetch their DDLs and sample their data.

**Parameters**

- `root_dir` \[`str`\]: Directory to write content in/fetch content from.
- `write_dict` \[`str`\]: If provided, write the details JSON to that path.

**Returns**

- \[`dict[str, typing.Any]`\]: Dictionary of objects encountered, indexed by their
  respective long names.

# Module `utils`

Common tools, parsers and helpers.

**Functions**

- [`clean_query()`](#utilsclean_query): Deep-cleaning of a SQL query.
- [`family_tree()`](#utilsfamily_tree): Identify imports of an object.
- [`fetch_children()`](#utilsfetch_children): Extract objects from
  `ALTER`/`CREATE`/`INTO`/`REFRESH`/`UPDATE` statements. Skip
- [`fetch_parents()`](#utilsfetch_parents): Extract objects from
  `FROM`/`JOIN`/`LOCATION` statements. Skip temporary ones.

## Functions

### `utils.clean_query`

```python
clean_query(query: str) -> str:
```

Deep-cleaning of a SQL query.

**Parameters**

- `query` \[`str`\]: The SQL query.

**Returns**

- \[`str`\]: Cleaned up query.

### `utils.family_tree`

```python
family_tree(objects: dict[str, typing.Any]) -> list[dict[str, list[str] | str]]:
```

Identify imports of an object.

**Parameters**

- `objects` \[`dict[str, typing.Any]`\]: Dictionary of objects encountered, indexed by
  their respective long names.

**Returns**

- \[`list[dict[str, list[str] | str]]`\]: List of dictionary of name and parents/chilren
  lists.

### `utils.fetch_children`

```python
fetch_children(query: str, paths: list[str], database: str) -> list[dict[str, str]]:
```

Extract objects from `ALTER`/`CREATE`/`INTO`/`REFRESH`/`UPDATE` statements. Skip
temporary ones.

**Parameters**

- `query` \[`str`\]: The DDL to parse.
- `paths` \[`list[str]`\]: List of object full paths.
- `database` \[`str`\]: Limit the matching to a specific database.

**Returns**

- \[`list[dict[str, str]]`\]: List of permanent objects encountered in various SQL
  statements (see below).

**Notes**

Regexes:

- `ALTER MATERIALIZED VIEW\s+([^(].*?)\s`
- `ALTER TABLE\s+([^(].*?)\s`
- `CREATE\s+.*\s+MATERIALIZED VIEW\s+([^(].*?)\s`
- `CREATE\s+.*\s+TABLE IF NOT EXISTS\s+([^(].*?)\s`
- `CREATE\s+.*\s+TABLE\s+([^(].*?)\s`
- `CREATE\s+.*\s+VIEW\s+([^(].*?)\s`
- `INSERT INTO\s+([^(].*?)\s`
- `REFRESH MATERIALIZED VIEW\s+([^(].*?)\s`
- `SELECT\s+.*\s+INTO\s+([^(].*?)\s`
- `UPDATE\s+([^(].*?)\s`

This whole thing starts to need unittesting...

### `utils.fetch_parents`

```python
fetch_parents(query: str, paths: list[str], database: str) -> list[dict[str, str]]:
```

Extract objects from `FROM`/`JOIN`/`LOCATION` statements. Skip temporary ones.

**Parameters**

- `query` \[`str`\]: The DDL to parse.
- `paths` \[`list[str]`\]: List of object full paths.
- `database` \[`str`\]: Limit the matching to a specific database.

**Returns**

- \[`list[dict[str, str]]`\]: List of permanent objects encountered in `FROM ...`,
  `JOIN ...` or `LOCATION ...` statements.

**Notes**

Regexes:

- `FROM\s+([^(].*?)[(\s;)]`
- `JOIN\s+([^(].*?)[(\s)]`
- `LOCATION\s+'(.*)'`
