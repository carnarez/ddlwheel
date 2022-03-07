# Module `sql`

Parse a SQL script and extract aliases, column and table lineage/dependencies.

**Usage**

```shell
$ python sql.py [SCRIPT.sql [SCRIPT.sql [...]]]
```

**Functions**

- [`clean_query()`](#sqlclean_query): Deep-cleaning of the SQL query.
- [`parse_query()`](#sqlparse_query): Parse query to extract schemas, table/views and
  columns; with aliases.
- [`through_ast()`](#sqlthrough_ast): Refine what we need by cleaning up/reformating the
  flattened AST.

**Classes**

- [`Feature`](#sqlfeature): Describe a column.
- [`Collection`](#sqlcollection): Describe a table or a view.

## Functions

### `sql.clean_query`

```python
clean_query(q: str) -> str:
```

Deep-cleaning of the SQL query.

**Parameters**

- `q` \[`str`\]: The SQL query.

**Returns**

- \[`str`\]: Cleaned up query.

### `sql.parse_query`

```python
parse_query(q: str) -> dict:
```

Parse query to extract schemas, table/views and columns; with aliases.

**Parameters**

- `q` \[`str`\]: The SQL query.

**Returns**

- \[`dict[str, dict[str, dict[str, str]]]`\]: Dictionary of schemas, table/views
  (including emporary objects) and columns (including aliases).

### `sql.through_ast`

```python
through_ast(ast: dict) -> dict:
```

Refine what we need by cleaning up/reformating the flattened AST.

**Parameters**

- `ast` \[`dict[str, typing.Any]`\]: The Abstract Syntax Tree of the query as parsed by
  `sqlfluff.parse()`.

**Returns**

- \[`dict[str, dict[str, dict[str, str]]]`\]: Dictionary of schemas, tables/views
  (including temporary objects) and columns.

## Classes

### `sql.Feature`

Describe a column.

#### Constructor

```python
Feature(**kwargs)
```

Initiate the object.

**Attributes**

### `sql.Collection`

Describe a table or a view.

#### Constructor

```python
Collection(features: list)
```

Initiate the object.

**Attributes**
