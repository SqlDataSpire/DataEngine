# DataEngine

A lightweight Python wrapper around SQLAlchemy, pandas, pyodbc, psycopg2, and pymongo that provides a unified interface for connecting to SQL Server, PostgreSQL, and MongoDB.

Connection strings are stored in a single `database.env` file and loaded at runtime — no credentials in code.

---

## Installation

Requires Python >= 3.10 and an active virtual environment.

```bash
pip install Python-DataEngine
```

To force a reinstall:

```bash
pip install --force-reinstall Python-DataEngine
```

### SQL Server prerequisite

DataEngine uses pyodbc and requires a Microsoft ODBC driver. Supported drivers in order of preference:

1. ODBC Driver 18 for SQL Server *(recommended)*
2. ODBC Driver 17 for SQL Server
3. SQL Server Native Client 11.0
4. SQL Server

Download: https://go.microsoft.com/fwlink/?linkid=2266640

---

## Quick Start

```python
import DataEngine

DataEngine.initialize()  # loads database.env and creates connection objects

db = DataEngine.alchemyObjects["my_connection"]
rows = db.query("SELECT TOP 10 * FROM dbo.MyTable")
```

---

## Connection Configuration

Connections are stored in a file named `database.env` in your working directory. Each entry is a JSON object under the `databases` key.

```
databases = '{"my_connection": {"type": "mssql", "server": "MYSERVER", "database": "MyDB", "UN": "", "PW": "", "trusted": "yes"}}'
```

All values must be strings. Use the interactive builder to create this file:

```python
DataEngine.connectionStringBuilder()
```

### Connection document schema

| Field | Description |
|---|---|
| `type` | `"mssql"`, `"postgres"`, or `"mongo"` |
| `server` | Server hostname or IP |
| `database` | Database name |
| `UN` | Username — leave blank `""` where not needed |
| `PW` | Password — leave blank `""` where not needed |
| `trusted` | `"yes"` for Windows Authentication (SQL Server only), `"no"` otherwise |

---

## SQL Server — `SqlConnectionObject`

Supports three authentication modes, selected automatically based on the values in `database.env`:

| `trusted` | `UN` | `PW` | Auth mode |
|---|---|---|---|
| `"yes"` | — | — | Windows Authentication (on-prem, NTLM/Kerberos) |
| `"no"` | ✓ | ✓ | SQL Server login |
| `"no"` | ✓ | — | Azure AD Interactive (MFA browser prompt, pre-fills username) |
| `"no"` | — | — | Azure AD Integrated (silent SSO using cached token) |

Azure AD Interactive caches its token for approximately one hour, after which it silently re-authenticates using the cached session.

### Methods

| Method | Returns | Description |
|---|---|---|
| `query(sql)` | `list[Row]` | Execute a SELECT and return all rows |
| `getTable(sql)` | `DataFrame` | Execute a SELECT and return a pandas DataFrame |
| `chunkTable(sql, chunksize)` | `Generator[DataFrame]` | Stream results in DataFrame chunks |
| `queryStream(sql)` | `Generator[Row]` | Stream results row by row |
| `execute(sql)` | — | Execute a non-result statement (INSERT, UPDATE, DELETE) |
| `executeProcedure(name)` | — | Execute a stored procedure by name |
| `truncateTable(schema, name)` | — | Truncate a table |
| `interop(sql)` | `int` | Execute an INSERT and return the new `scope_identity()` |

### Example

```python
import DataEngine

DataEngine.initialize()
sql = DataEngine.alchemyObjects["sql"]

# Query to a list of rows
rows = sql.query("SELECT id, name FROM dbo.Users WHERE active = 1")

# Query to a DataFrame
df = sql.getTable("SELECT * FROM dbo.Sales")

# Stream a large result set in chunks
for chunk in sql.chunkTable("SELECT * FROM dbo.BigTable", chunksize=10000):
    process(chunk)

# Execute a stored procedure
sql.executeProcedure("dbo.usp_RefreshSummary")

# Insert and get the new row ID
new_id = sql.interop("INSERT INTO dbo.Log (message) VALUES ('started')")
```

---

## PostgreSQL — `PgConnectionObject`

Connects via psycopg2. Always requires `UN` and `PW`.

### Methods

The same interface as `SqlConnectionObject`: `query`, `getTable`, `chunkTable`, `queryStream`, `execute`, `executeProcedure`, `truncateTable`.

### Example

```python
import DataEngine

DataEngine.initialize()
pg = DataEngine.alchemyObjects["postgres"]

df = pg.getTable("SELECT * FROM public.orders WHERE status = 'open'")
```

---

## MongoDB — `MongoConnectionObject`

Connects via pymongo using a standard `mongodb://` URI with `authSource=admin`.

### Methods

| Method | Returns | Description |
|---|---|---|
| `query(collection, query)` | `Cursor` | Find documents matching a query dict |
| `aggregate(collection, pipeline)` | `Cursor` | Run an aggregation pipeline |
| `dropDatabase(database)` | `str` | Drop a database |
| `mongoImport(**kwargs)` | `MongoResult` | Bulk import via `mongoimport.exe` |

### Example

```python
import DataEngine

DataEngine.initialize()
mongo = DataEngine.alchemyObjects["mongo"]

cursor = mongo.query("users", {"active": True})
for doc in cursor:
    print(doc)

result = mongo.aggregate("sales", [
    {"$match": {"year": 2025}},
    {"$group": {"_id": "$region", "total": {"$sum": "$amount"}}}
])
```

---

## Module-level API

| Function | Description |
|---|---|
| `initialize()` | Load `database.env` and populate `alchemyObjects` |
| `connectionStringBuilder()` | Interactive prompt to create or add connection entries |
| `connectionGenerator(dict)` | Build connection objects from a dict (bypasses `.env`) |
| `saveConnectionStrings()` | Persist `alchemyConnections` back to `database.env` |
| `checkOdbcDriver()` | Print which ODBC driver DataEngine has selected |
| `help()` | Print usage summary and active connections |

After `initialize()`, connections are available in:

```python
DataEngine.alchemyObjects   # dict of connection objects, keyed by name
DataEngine.alchemyConnections  # dict of raw connection string dicts
```

---

## Development

Install dev dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite (no live database required — all tests are mocked):

```bash
pytest
```
