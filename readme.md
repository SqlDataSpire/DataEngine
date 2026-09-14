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

> ⚠️ **`database.env` is plaintext — it is not encrypted.** Prefer Windows Auth or Azure AD over a stored password, or skip the file entirely and configure connections programmatically. See [Two ways to use DataEngine](#two-ways-to-use-dataengine) below.

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

## Two ways to use DataEngine

DataEngine supports two distinct consumption models. They are separate use cases with separate credential stories — pick the one that matches your program, and don't mix them.

| | **Declarative** (default) | **Programmatic** |
|---|---|---|
| Who uses it | Unattended jobs, ETL, schedulers, services | Interactive tools (Typer/Click CLIs), notebooks, apps that already own their config |
| Config source | `database.env`, read automatically | Whatever the host program supplies |
| Setup | `import DataEngine` — that's it | Construct connection objects directly |
| Credentials | Must already be on disk, or be ambient (Windows/Azure AD) | Supplied at call time — vault, prompt, platform secret |
| `database.env` | Required | Not used |

### Declarative — zero input

This is what DataEngine is built for. Importing the package auto-initializes it: `database.env` is read, every connection document is turned into a live object, and `alchemyObjects` is populated. No calls, no arguments, no prompts.

```python
import DataEngine                      # already initialized

db = DataEngine.alchemyObjects["main"]
df = db.getTable("SELECT * FROM dbo.Sales")
```

Because there is no interactive moment in this mode, **there is nowhere to inject a secret** — the credential must already be resolvable when the process starts. That makes ambient authentication the right answer here, not a fallback:

1. **Windows Authentication** (`"trusted": "yes"`) — the job runs as a service account; no credential is stored anywhere.
2. **Azure AD Integrated** — leave `UN` and `PW` blank. The ODBC driver uses a cached token. See the auth table under [SQL Server](#sql-server--sqlconnectionobject).
3. **A platform-injected environment variable** read into `database.env`'s place by your deployment tooling.

<a id="security"></a>
### ⚠️ Credentials in `database.env` are stored in plaintext

**`database.env` is not encrypted.** Any `PW` value in it is readable by anyone who can read the file, and `saveConnectionStrings()` writes it straight to disk in the clear. `connectionStringBuilder()` will happily prompt for a password and persist it the same way. The file is a deployment convenience, not a secrets store.

If your environment forbids at-rest plaintext credentials, do not put a password in `database.env` at all — use ambient auth above, or use the programmatic mode below.

Keep `database.env` out of source control (`*.env` is already in this repo's `.gitignore`). If a password has already been committed, rotate it — removing the file from the working tree does not remove it from git history.

### Programmatic — the host program owns the credentials

An interactive or self-configuring program does not need `database.env`. `SqlConnectionObject`, `PgConnectionObject`, and `MongoConnectionObject` are exported at package level and can be constructed directly, so a Typer CLI, a web service, or a notebook can resolve a credential however it likes — a prompt, a key vault, a platform secret — and hand it in at call time. Nothing touches disk.

```python
import typer
import DataEngine
from DataEngine import SqlConnectionObject

def main(server: str, database: str, username: str,
         password: str = typer.Option(..., prompt=True, hide_input=True)):

    db = SqlConnectionObject(
        name="main",
        server=server,
        database=database,
        UN=username,
        PW=password,          # never written to database.env
        trusted="no",
    )

    # Optional: register it so the rest of your code resolves it by name
    DataEngine.alchemyObjects["main"] = db

    print(db.getTable("SELECT TOP 10 * FROM dbo.Sales"))

typer.run(main)
```

The resulting object is identical to one built from `database.env` — same methods, same `.connection` / `.engine` / `.session` layers. Only the source of the configuration differs.

Two notes when running in this mode:

- Importing DataEngine still attempts to auto-initialize. With no `database.env` present it prints a notice and continues; `alchemyObjects` is simply empty and yours to populate.
- Do **not** call `saveConnectionStrings()` — it serializes `alchemyConnections` to `database.env` in plaintext, which is exactly what this mode is avoiding.

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

## Direct Connection Access

Both `SqlConnectionObject` and `PgConnectionObject` expose three layers of the underlying connection stack for advanced workflows:

| Attribute | Type | Use it for |
| :--- | :--- | :--- |
| `.connection` | `str` | The driver-compatible connection string (pyodbc for SQL Server, psycopg2 for PostgreSQL). Hand it to any library that takes a DSN, or to your own `create_engine()`. |
| `.engine` | `sqlalchemy.engine.Engine` | The `create_engine()` object. **This is what pandas wants** — pass it to `pd.read_sql()` / `DataFrame.to_sql()`. Also the route to a raw DB-API connection. |
| `.session` | `sqlalchemy.orm.scoping.scoped_session` | The SQLAlchemy **ORM** layer — mapped classes, `session.query()`, unit-of-work transactions. Thread-local. |

> **`.connection` is a string, not an open connection.** It holds the DSN, not a live handle. For a real DB-API 2.0 connection (with `.cursor()`), use `db.engine.raw_connection()`.

The string differs by backend:

| Backend | Shape of `.connection` |
| :--- | :--- |
| SQL Server | `mssql+pyodbc:///?odbc_connect=<url-encoded ODBC string>` |
| PostgreSQL | `postgresql+psycopg2://<user>:<pw>@<server>/<database>` |

### Example

```python
import urllib.parse
import pandas as pd
import DataEngine
from sqlalchemy import create_engine, text, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base

DataEngine.initialize()
db = DataEngine.alchemyObjects["my_connection"]

# ── 1. .connection — the driver connection string ────────────────────────────
# Build your own engine with different pool or logging options:
custom_engine = create_engine(db.connection, pool_size=20, echo=True)

# For SQL Server, recover the plain ODBC string for a direct pyodbc.connect():
odbc = urllib.parse.unquote_plus(db.connection.split("odbc_connect=")[1])

# ── 2. .engine — pandas and SQLAlchemy Core ──────────────────────────────────
df = pd.read_sql("SELECT * FROM dbo.Sales", db.engine)
df.to_sql("SalesStaging", db.engine, schema="dbo", if_exists="append", index=False)

with db.engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))   # text() is required on SQLAlchemy 2.x

raw_conn = db.engine.raw_connection()          # live pyodbc / psycopg2 connection
cursor = raw_conn.cursor()
cursor.execute("SELECT 1")

# ── 3. .session — the ORM ────────────────────────────────────────────────────
Base = declarative_base()

class User(Base):
    __tablename__ = "Users"
    __table_args__ = {"schema": "dbo"}
    id = Column(Integer, primary_key=True)
    name = Column(String)
    active = Column(Boolean)

session = db.session()
try:
    user = session.query(User).filter(User.id == 1).one()
    user.active = False
    session.commit()
except Exception:
    session.rollback()
    raise
finally:
    db.session.remove()   # always release the thread-local session
```

For pooled connections without touching the engine directly, the objects also expose `getConnection()` and `getStreamingConnection()` — the latter sets `stream_results=True` for large result sets.

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
| `initialize()` | Load `database.env` and populate `alchemyObjects`. Runs automatically on import — you rarely need to call it yourself. |
| `connectionGenerator()` | Reload `database.env` and rebuild `alchemyObjects` from it. The declarative path. |
| `connectionGenerator(dict)` | Build connection objects from a supplied dict, bypassing `database.env` entirely. The programmatic path. |
| `connectionStringBuilder()` | Interactive prompt to create or add connection entries. ⚠️ Persists any password you enter to `database.env` in plaintext. |
| `saveConnectionStrings()` | Persist `alchemyConnections` back to `database.env`. ⚠️ Plaintext — see [Security](#security). |
| `checkOdbcDriver()` | Print which ODBC driver DataEngine has selected |
| `help()` | Print usage summary and active connections |

Both forms of `connectionGenerator()` populate the same registry:

```python
DataEngine.alchemyObjects      # dict of connection objects, keyed by name
DataEngine.alchemyConnections  # dict of connection documents, keyed by name
```

The two forms differ in one respect worth knowing. `connectionGenerator()` with no argument refreshes `alchemyConnections` from disk; `connectionGenerator(dict)` does **not** copy the supplied dict into it. That is deliberate — `alchemyConnections` is what `saveConnectionStrings()` serializes to `database.env` in plaintext, so a credential handed in at runtime cannot be written to disk as a side effect of building the connection.

### Supplying your own connection documents

Each value follows the [connection document schema](#connection-document-schema), but only three keys are required. The rest default to the values that mean "not used", so a hand-built document carries only what is relevant to its auth mode:

| Key | Required | Default |
|---|---|---|
| `type` | ✔ | — |
| `server` | ✔ | — |
| `database` | ✔ | — |
| `UN` | | `""` |
| `PW` | | `""` |
| `trusted` | | `"no"` |

```python
# Windows auth — no credentials to supply
DataEngine.connectionGenerator({
    "main": {
        "type": "mssql",
        "server": "MYSERVER",
        "database": "MyDB",
        "trusted": "yes",
    },
})

# SQL login — trusted defaults to "no"
DataEngine.connectionGenerator({
    "main": {
        "type": "mssql",
        "server": "MYSERVER",
        "database": "MyDB",
        "UN": username,
        "PW": password,
    },
})
```

Omitting one of the three required keys raises `KeyError`. A `type` outside `"mssql"`, `"postgres"`, and `"mongo"` raises `ValueError` naming both the offending type and the connection it came from.

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
