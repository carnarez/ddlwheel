"""Database-flavoured utils and functions.

In particular, three functions are expected in each engine module:
* `fetch_objects()` listing all database objects to describe.
* `fetch_ddl()` querying the definition of a single object (DDL) which will later be
  parsed to extract direct parents.
* `fetch_details()` which does all the work, that is, leverages the previous functions
  to "fully" describe all objects in the database(s).
"""
