import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker
import pandas as pd
from pyodbc import drivers
from .storedprocedure import StoredProcedure


def _get_pyodbc_driver() -> str:
    prefs = [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",
    ]
    installed = set(drivers())
    for drv in prefs:
        if drv in installed:
            return drv
    raise RuntimeError("No supported SQL Server ODBC driver found.")


def _build_odbc_string(server: str, database: str, UN: str | None = None, PW: str | None = None, trusted: bool = False) -> str:
    """
    Builds a pyodbc connection string for one of three SQL Server auth modes:

      1. Windows Authentication  (trusted=True)
         Uses the current Windows identity — no credentials required.

      2. SQL Server Authentication  (UN + PW provided)
         Classic username/password login against SQL Server's own user store.

      3. Azure Active Directory
         a. ActiveDirectoryIntegrated  (no UN, no PW) — silent SSO using a
            cached token from a prior interactive session. Zero prompts when
            a valid token exists.
         b. ActiveDirectoryInteractive  (UN provided, no PW) — MFA browser
            pop-up, pre-filled with the supplied username. The ODBC driver
            caches the resulting token so subsequent calls within ~1 hour
            fall through to (a).
    """
    base = (
        f"DRIVER={{{_get_pyodbc_driver()}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"TrustServerCertificate=yes;"
    )

    if trusted:
        return base + "Trusted_Connection=yes;"

    if UN and PW:
        return base + f"UID={UN};PWD={PW};"

    if UN:
        return base + f"UID={UN};Authentication=ActiveDirectoryInteractive;"

    return base + "Authentication=ActiveDirectoryIntegrated;"

from ..base import BaseRdbmsConnectionObject


class SqlConnectionObject(BaseRdbmsConnectionObject):
    def __init__(self, **kwargs):
        name     = kwargs["name"]
        server   = kwargs["server"]
        database = kwargs["database"]
        un       = kwargs.get("UN")
        pw       = kwargs.get("PW")
        trusted  = kwargs.get("trusted", False)
        if isinstance(trusted, str):
            trusted = trusted.strip().lower() == "yes"

        odbc = _build_odbc_string(server, database, UN=un, PW=pw, trusted=trusted)
        conx = f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc)}"

        engine  = create_engine(conx, fast_executemany=True)
        session = scoped_session(sessionmaker(bind=engine))
        super().__init__(name, conx, engine=engine, session=session)

    def _format_procedure_sql(self, procedure_name: str) -> str:
        return f"set nocount on; exec {procedure_name};"

    def interop(self, insert_command) -> int:
        con = self.engine.raw_connection()
        cur = con.cursor()
        cur.execute(insert_command)
        newid = cur.execute("select scope_identity() as new_id").fetchone()
        con.commit()
        return int(newid[0])
