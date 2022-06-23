# Module `__init__`

Extract information of SQL objects from a database.

**Usage**

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

```python
from wheel import family_tree

with open("data.json", "w") as f:
    f.write(json.dumps(family_tree(r.objects)))
```

# Module `engines`

Template object for flavoured clients; act as documentation.

**Classes**

- [`Engine`](#enginesengine): Metaclass documenting the necessary minimal
  implementation.

## Classes

### `engines.Engine`

Metaclass documenting the necessary minimal implementation.

**Methods**

- [`fetch_ddl()`](#enginesenginefetch_ddl): Fetch the DDL of an object.
- [`fetch_columns()`](#enginesenginefetch_columns): List all columns from an object.
- [`fetch()`](#enginesenginefetch): List all objects in all databases and fetch all
  information for each.
- [`fetch_objects()`](#enginesenginefetch_objects): List all objects in all accessible
  databases.
- [`dump_objects()`](#enginesenginedump_objects): Dump the `objects` dictionary in JSON
  format to the given path.

#### Constructor

```python
Engine(**connection_kwargs)
```

Set up the connection parameters and class objects.

**Parameters**

- `connection_kwargs` \[`dict[str, int | str]`\]: Connection parameters to connect to
  the given database.

**Attributes**

- `config` \[`dict[str, int | str]`\]: Connection parameters to connect to the given
  database.
- `connections` \[`dict[str, object]`\]: Dictionary of connection objects (type specific
  to the database client) for each database encountered.
- `objects` \[`dict[str, typing.Any]`\]: Dictionary of objects encountered, indexed by
  their respective long names.

#### Methods

##### `engines.Engine.fetch_ddl`

```python
fetch_ddl(cursor, *args, **kwargs) -> str:
```

Fetch the DDL of an object.

**Parameters**

- `cursor`: Cursor (object type specific to the database client) to use to run the
  query.

**Returns**

- \[`str`\]: DDL of the object.

**Decoration** via `@staticmethod`.

##### `engines.Engine.fetch_columns`

```python
fetch_columns(cursor, *args, **kwargs) -> list[dict[str, str]]:
```

List all columns from an object.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor (object type specific to the
  database client) to use to run the query.

**Returns**

- \[`list[dict[str, str]]`\]: Dictionary describing the object columns (name,
  datatypes).

**Decoration** via `@staticmethod`.

##### `engines.Engine.fetch`

```python
fetch():
```

List all objects in all databases and fetch all information for each.

##### `engines.Engine.fetch_objects`

```python
fetch_objects(cursor):
```

List all objects in all accessible databases.

This method should also generate connection objects (type specific to the database
client) for each accessible database; stored in the `connections` dictionary.

**Parameters**

- `cursor`: Cursor (object type specific to the database client) to use to run the
  query.

##### `engines.Engine.dump_objects`

```python
dump_objects(path = "objects.json"):
```

Dump the `objects` dictionary in JSON format to the given path.

**Parameters**

- `path` \[`str`\]: Write the `objects` dictionary in JSON format to that path.

# Module `engines.redshift`

`Redshift` facilities.

**Classes**

- [`Redshift`](#enginesredshiftredshift): `Redshift` client object.

## Classes

### `engines.redshift.Redshift`

`Redshift` client object.

**Methods**

- [`fetch_columns()`](#enginesredshiftredshiftfetch_columns): List all columns from an
  object.
- [`fetch_ddl()`](#enginesredshiftredshiftfetch_ddl): Fetch the DDL of an object.
- [`fetch()`](#enginesredshiftredshiftfetch): List all objects in all databases and
  fetch all information for each.
- [`fetch_objects()`](#enginesredshiftredshiftfetch_objects): List all objects in all
  `Redshift` databases.
- [`fetch_procs()`](#enginesredshiftredshiftfetch_procs): List all stored procedures in
  all schemas of a `Redshift` database.

#### Constructor

```python
Redshift(**connection_kwargs)
```

Set up the connection parameters and class objects.

**Parameters**

- `connection_kwargs` \[`dict[str, int | str]`\]: Connection parameters to connect to
  the `Redshift` database.

**Attributes**

- `config` \[`dict[str, int | str]`\]: Connection parameters to connect to the
  `Redshift` database.
- `connections` \[`dict[str, redshift_connector.Connection]`\]: Dictionary of connection
  objects for each database encountered.
- `objects` \[`dict[str, typing.Any]`\]: Dictionary of objects encountered, indexed by
  their respective long names.

#### Methods

##### `engines.redshift.Redshift.fetch_columns`

```python
fetch_columns(cursor: Cursor, n: str, s: str, d: str) -> list[dict[str, str]]:
```

List all columns from an object.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.
- `n` \[`str`\]: Name of the object.
- `s` \[`str`\]: Name of the schema hosting the object.
- `d` \[`str`\]: Name of the database hosting the schema.

**Returns**

- \[`list[dict[str, str]]`\]: Dictionary describing the object columns (name,
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

**Decoration** via `@staticmethod`.

##### `engines.redshift.Redshift.fetch_ddl`

```python
fetch_ddl(cursor: Cursor, n: str, s: str, d: str, t: str) -> str:
```

Fetch the DDL of an object.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.
- `n` \[`str`\]: Name of the object.
- `s` \[`str`\]: Name of the schema hosting the object.
- `d` \[`str`\]: Name of the database hosting the schema.
- `t` \[`str`\]: One of `external table`, `procedure`, `table` or `view` (last one
  accounting for materialized views as well).

**Returns**

- \[`str`\]: DDL of the object.

**Notes**

Performing the following \[example\] query:

```sql
show external table schema.table
```

**Decoration** via `@staticmethod`.

##### `engines.redshift.Redshift.fetch`

```python
fetch():
```

List all objects in all databases and fetch all information for each.

##### `engines.redshift.Redshift.fetch_objects`

```python
fetch_objects(cursor: Cursor):
```

List all objects in all `Redshift` databases.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.

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

##### `engines.redshift.Redshift.fetch_procs`

```python
fetch_procs(cursor: Cursor, d: str):
```

List all stored procedures in all schemas of a `Redshift` database.

**Parameters**

- `cursor` \[`redshift_connector.cursor.Cursor`\]: Cursor to use to run the query.
- `d` \[`str`\]: Name of the database hosting the schema.

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

# Module `parsers`

Entrypoint for a simplified SQL parser.

# Module `parsers.common`

Common tools, parsers and helpers.

**Functions**

- [`clean_query()`](#parserscommonclean_query): Deep-cleaning of a SQL query.
- [`fetch_children()`](#parserscommonfetch_children): Extract objects from various SQL
  statements. Skip temporary ones.
- [`fetch_parents()`](#parserscommonfetch_parents): Extract objects from
  `FROM`/`JOIN`/`LOCATION` statements. Skip temporary ones.

## Functions

### `parsers.common.clean_query`

```python
clean_query(query: str) -> str:
```

Deep-cleaning of a SQL query.

**Parameters**

- `query` \[`str`\]: The SQL query.

**Returns**

- \[`str`\]: Cleaned up query.

### `parsers.common.fetch_children`

```python
fetch_children(query: str, paths: list[str], database: str) -> list[dict[str, str]]:
```

Extract objects from various SQL statements. Skip temporary ones.

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

### `parsers.common.fetch_parents`

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

# Module `wheel`

Facilities to generate input for the wheel.

**Functions**

- [`family_tree()`](#wheelfamily_tree): Identify imports of an object.

## Functions

### `wheel.family_tree`

```python
family_tree(objects: dict[str, typing.Any]) -> list[dict[str, list[str] | str]]:
```

Identify imports of an object.

**Parameters**

- `objects` \[`dict[str, typing.Any]`\]: Dictionary of objects encountered, indexed by
  their respective long names.

**Returns**

- \[`list[dict[str, list[str] | str]]`\]: List of dictionary of name and
  parents/children lists.
