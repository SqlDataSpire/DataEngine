"""An engine for managing SQL data transitions."""
import os
import importlib
import pathlib
import warnings
import sys
import json
from dotenv import load_dotenv

# CHICKEN & EGG FIX: Only import the heavy database packages if we are NOT building the package
if "flit" not in sys.modules and "build" not in sys.modules:
    from .base import BaseRdbmsConnectionObject
    from .mssql import SqlConnectionObject, getPyodbcDriver
    from .postgres import PgConnectionObject
    from .mysql import MysqlConnectionObject
    from .oracle import OracleConnectionObject
    from .generic import GenericConnectionObject
    from .mongo import MongoConnectionObject, MongoResult

# flit reads this as the package version (pyproject declares it dynamic)
__version__ = "2.5.0"

alchemyConnections = {}
alchemyObjects = {}

def checkOdbcDriver():
    if "flit" in sys.modules or "build" in sys.modules:
        return
    if getPyodbcDriver() == '':
        print("""
        DataEngine did not find a suitable ODBC driver. Please install the latest ODBC driver from MS https://go.microsoft.com/fwlink/?linkid=2266640
        """)
    else:
        print(f"using: {getPyodbcDriver()}")

def help():
    print("Interface for creating wrappers for Database Objects")
    print("SqlConnectionObject() for SQL Server")
    print("PgConnectionObject() for PostgreSQL")
    print("MysqlConnectionObject() for MySQL & MariaDB")
    print("OracleConnectionObject() for Oracle")
    print("GenericConnectionObject() for custom connection strings & other databases")
    print("MongoConnectionObject() for Mongo")
    print("format for a database connection document which are strings saved in 'database.env':" )
    print('{"$name":{"type":"[mssql|postgres|mysql|mariadb|oracle|mongo|generic]","database":"","server":"","UN":"","PW":"","trusted":"[yes|no]"}}' )
    print("where $name is the contextual name for the connection, like 'main','data', or 'library'" )
    print("")
    print("DataEngine Command List:")
    print("initialize() - load connection elements in database.env to connection alchemyObjects{}")
    print("connectionStringBuilder() create or add new connection strings to database.env(beware storing sensitive passwords...)")
    print("connectionGenerator() convert alchemyConnections{} strings to  alchemyObjects{}")
    print("saveConnectionStrings() save all elements in alchemyConnections{} to database.env")
    print("")
    print("")
    print("Active Connection Object Names:")
    print("\r\n".join(alchemyObjects.keys()))
    print("-------")
    print("active connections strings:")
    print(f"alchemyConnections = {alchemyConnections}")
    print("-------")
    print("active connections objects")
    print(f"alchemyObjects = {alchemyObjects}")
    print("-------")

def _resolve_password(name: str, un: str, raw_pw: str) -> str:
    """Resolves connection password from an external response file, environment variable,
    interactive terminal prompt, or explicit literal string.

    Supported patterns:
      - 'file:<path>': Read the single-line password from an external file.
      - '${VAR_NAME}': Read password from an OS environment variable.
      - 'prompt': Prompt interactively at connect-time using getpass.
      - Any other string: Treated as the literal password.
    """
    if not raw_pw:
        return ""

    # 1. External password / response file
    if raw_pw.startswith("file:"):
        path = pathlib.Path(raw_pw[5:]).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Password file not found for connection '{name}': {path}")
        lines = path.read_text().splitlines()
        return lines[0].strip() if lines else ""

    # 2. Environment variable reference ${VAR}
    if raw_pw.startswith("${") and raw_pw.endswith("}"):
        var_name = raw_pw[2:-1]
        return os.environ.get(var_name, "")

    # 3. Connect-time interactive prompt
    if raw_pw.lower() == "prompt":
        if sys.stdin and sys.stdin.isatty():
            import getpass
            label = f" ({un})" if un else ""
            return getpass.getpass(f"DataEngine: enter password for connection '{name}'{label}: ")
        raise RuntimeError(
            f"Connection '{name}' specifies 'prompt', but no interactive terminal (TTY) is available."
        )

    # 4. Literal password
    return raw_pw

def connectionGenerator(connectionList: dict = None):
    global alchemyObjects
    global alchemyConnections
    if connectionList is None:
        load_dotenv("database.env")
        alchemyConnections = json.loads(os.environ["databases"])
        connectionList = alchemyConnections
    # A caller-supplied dict is used as-is and deliberately NOT written to
    # alchemyConnections — that global is what saveConnectionStrings() persists
    # to database.env in plaintext, so credentials passed in memory stay in memory.
    for dbs in connectionList.keys():
        _t = connectionList[dbs]["type"]
        if _t == "generic":
            conx = (
                connectionList[dbs].get("connection")
                or connectionList[dbs].get("connection_string")
                or connectionList[dbs].get("url")
            )
            engine_kwargs = connectionList[dbs].get("engine_kwargs") or {}
            alchemyObjects[dbs] = GenericConnectionObject(name=dbs, connection=conx, engine_kwargs=engine_kwargs)
            continue

        server = connectionList[dbs]["server"]
        database = connectionList[dbs]["database"]
        # Optional: a document built by hand need not carry keys the auth mode
        # makes meaningless (UN/PW under Windows auth, trusted under postgres).
        un = connectionList[dbs].get("UN", "")
        raw_pw = connectionList[dbs].get("PW", "")
        pw = _resolve_password(dbs, un, raw_pw)
        trusted = connectionList[dbs].get("trusted", "no")

        if _t == "mssql":
            alchemyObjects[dbs] = SqlConnectionObject(**{"name": dbs, "server": server, "database": database, "UN": un, "PW": pw, "trusted": trusted})
        elif _t == "postgres":
            port = connectionList[dbs].get("port")
            alchemyObjects[dbs] = PgConnectionObject(**{"name": dbs, "server": server, "database": database, "UN": un, "PW": pw, "trusted": trusted, "port": port})
        elif _t in ("mysql", "mariadb"):
            port = connectionList[dbs].get("port", 3306)
            charset = connectionList[dbs].get("charset", "utf8mb4")
            alchemyObjects[dbs] = MysqlConnectionObject(**{"name": dbs, "server": server, "database": database, "UN": un, "PW": pw, "trusted": trusted, "port": port, "charset": charset})
        elif _t == "oracle":
            port = connectionList[dbs].get("port", 1521)
            service_name = connectionList[dbs].get("service_name")
            alchemyObjects[dbs] = OracleConnectionObject(**{"name": dbs, "server": server, "database": database, "UN": un, "PW": pw, "trusted": trusted, "port": port, "service_name": service_name})
        elif _t == "mongo":
            alchemyObjects[dbs] = MongoConnectionObject(**{"name": dbs, "server": server, "database": database, "UN": un, "PW": pw})
        else:
            raise ValueError(f"connection {dbs!r} has unknown type {_t!r} - expected 'mssql', 'postgres', 'mysql', 'mariadb', 'oracle', 'mongo' or 'generic'")

def saveConnectionStrings():
    cx = str(alchemyConnections).replace("'", '"')
    s = f"databases = '{cx}'"
    with open("./database.env", "w") as f:
        f.write(s)
    connectionGenerator()

def connectionStringBuilder():
    def validate(question, valid_responses):
        response = ""
        while True:
            _res = input(question)
            if _res in valid_responses:
                response = _res
                break
            else:
                print(f"valid reponses are: {','.join(valid_responses)}")
        return response

    def notBlank(question):
        response = ""
        while True:
            _res = input(question)
            if len(_res) > 0:
                response = _res
                break
            else:
                print(f"response must not be blank")
        return response

    _svr_type = validate("1=MSSQL | 2=POSTGRES | 3=MONGO | 4=MYSQL | 5=MARIADB | 6=ORACLE | 7=GENERIC?\r\n", ["1", "2", "3", "4", "5", "6", "7"])
    svr_type = ""
    match _svr_type:
        case "1":
            svr_type = "mssql"
        case "2":
            svr_type = "postgres"
        case "3":
            svr_type = "mongo"
        case "4":
            svr_type = "mysql"
        case "5":
            svr_type = "mariadb"
        case "6":
            svr_type = "oracle"
        case "7":
            svr_type = "generic"

    if svr_type == "generic":
        conx_str = notBlank("Full SQLAlchemy connection string (e.g. sqlite:///test.db, snowflake://...)?\r\n")
        name = notBlank("Finally, give this connection a name?")
        global alchemyConnections
        __conx = {"type": "generic", "connection": conx_str}
        print(__conx)
        correct = validate("is this correct? (Y/n)\r\n", ["Y", "n"])
        if correct == "n":
            connectionStringBuilder()
            return
        alchemyConnections[name] = __conx
        more = validate("Add another?(Y/n)", ["Y", "n"])
        if more == "Y":
            connectionStringBuilder()
        saveConnectionStrings()
        return

    server = notBlank("Server name?\r\n")
    database = notBlank("database name?\r\n")
    trusted = "no"
    username = ""
    password = ""
    if svr_type in ("mssql", "postgres", "mysql", "mariadb", "oracle"):
        _auth = validate("Windows Auth / Kerberos / OS External Auth? (Y/n)\r\n", ["Y", "n"])
        trusted = "yes" if _auth == "Y" else "no"
    if trusted == "no":
        print("\n--- SECURITY DISCLAIMER ---")
        print("Static passwords stored in database.env are insecure and not recommended.")
        print("DataEngine disclaims liability for leaked credentials.")
        print("Safe alternatives for the password prompt:")
        print("  - 'prompt'       : prompt securely at connect-time without storing on disk")
        print("  - 'file:<path>'  : load from a single-line response file with strict OS permissions")
        print("  - '${ENV_VAR}'   : read from a runtime environment variable")
        print("  - your password  : plaintext in database.env (use at your own discretion)")
        print("---------------------------\n")
        username = notBlank("User name?\r\n")
        password = notBlank("Password or secret reference ('prompt', 'file:<path>', '${VAR}')?\r\n")
    name = notBlank("Finally, give this connection a name?")
    __conx = {"type": svr_type, "database": database, "server": server, "UN": username, "PW": password, "trusted": trusted}
    print(__conx)
    correct = validate("is this correct? (Y/n)\r\n", ["Y", "n"])
    if correct == "n":
        connectionStringBuilder()
        return
    alchemyConnections[name] = __conx
    more = validate("Add another?(Y/n)", ["Y", "n"])
    if more == "Y":
        connectionStringBuilder()
    saveConnectionStrings()

def initialize():
    if load_dotenv("database.env") == False:
        print("the database.env file is empty. Import the DataEngine package then execute connectionStringBuilder()")
        return
    checkOdbcDriver()
    connectionGenerator()

# CRITICAL FIX: Only auto-initialize if we aren't compiling/building metadata
if "flit" not in sys.modules and "build" not in sys.modules:
    initialize()
