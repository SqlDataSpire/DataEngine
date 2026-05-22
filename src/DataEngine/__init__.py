from . import _version
import os
import importlib
import pathlib
import warnings
import sys
import json
from dotenv import load_dotenv

# CHICKEN & EGG FIX: Only import the heavy database packages if we are NOT building the package
if "flit" not in sys.modules and "build" not in sys.modules:
    from .mssql import SqlConnectionObject, getPyodbcDriver
    from .postgres import PgConnectionObject
    from .mongo import MongoConnectionObject, MongoResult

__version__ = _version.get_version()
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
    print("PgConnectionObject() for postres")
    print("SqlConnectionObject() for SQL server")
    print("MongoConnectionObject() for Mongo")
    print("format for a database connection document which are strings saved in 'database.env':" )
    print('{"$name":{"type":"[mssql|postgres|mongo]","database":"","server":"","UN":"","PW":"","trusted":"[yes|no]"}}' )
    print("where $name is the contextual name for the connextion, like 'main','data', or 'library'" )
    print("")
    print("DataEngine Command List:")
    print("intialize() - load connection elements in database.env to connection alchemyObjects{}")
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

def connectionGenerator(connectionList: dict = None):
    global alchemyObjects
    global alchemyConnections
    if connectionList is None:
        load_dotenv("database.env")
        alchemyConnections = json.loads(os.environ["databases"])
    connectionList = alchemyConnections
    for dbs in connectionList.keys():
        server = connectionList[dbs]["server"]
        database = connectionList[dbs]["database"]
        un = connectionList[dbs]["UN"]
        pw = connectionList[dbs]["PW"]
        trusted = connectionList[dbs]["trusted"]
        _t = connectionList[dbs]["type"]
        if _t == "mssql":
            alchemyObjects[dbs] = SqlConnectionObject(**{"name": dbs, "server": server, "database": database, "UN": un, "PW": pw, "trusted": trusted, } )
        if _t == "postgres":
            alchemyObjects[dbs] = PgConnectionObject(**{"name": dbs, "server": server, "database": database, "UN": un, "PW": pw, } )
        if _t == "mongo":
            alchemyObjects[dbs] = MongoConnectionObject(**{"name": dbs, "server": server, "database": database, "UN": un, "PW": pw, } )

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

    _svr_type = validate("1=MSSQL | 2=POSTGRES | 3=MONGO?\r\n", ["1", "2", "3"])
    svr_type = ""
    if _svr_type == "1":
        svr_type = "mssql"
    if _svr_type == "2":
        svr_type = "postgres"
    if _svr_type == "3":
        svr_type = "mongo"
        
    server = notBlank("Server name?\r\n")
    database = notBlank("database name?\r\n")
    trusted = "no"
    username = ""
    password = ""
    if svr_type == "mssql":
        _auth = validate("Windows Authentication? (Y/n)\r\n", ["Y", "n"])
        trusted = "yes" if _auth == "Y" else "no"
    if trusted == "no":
        username = notBlank("User name?\r\n")
        password = notBlank("Password?\r\n")
    name = notBlank("Finally, give this connection a name?")
    global alchemyConnections
    __conx = {"type": svr_type, "database": database, "server": server, "UN": username, "PW": password, "trusted": trusted, }
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
