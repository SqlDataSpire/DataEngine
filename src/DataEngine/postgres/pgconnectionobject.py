import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from ..base import BaseRdbmsConnectionObject


class PgConnectionObject(BaseRdbmsConnectionObject):
    def __init__(self, **kwargs):
        name = kwargs["name"]
        server = kwargs["server"]
        database = kwargs["database"]
        port = kwargs.get("port")
        host_part = f"{server}:{port}" if port else server

        _un = kwargs.get("UN", "") or ""
        _pw = kwargs.get("PW", "") or ""
        trusted = kwargs.get("trusted", False)
        if isinstance(trusted, str):
            trusted = trusted.strip().lower() == "yes"

        if trusted:
            user_part = f"{urllib.parse.quote_plus(_un)}@" if _un else "@"
            conx = f"postgresql+psycopg2://{user_part}{host_part}/{database}?gssencmode=prefer"
        elif _un and _pw:
            _unpw = f"{urllib.parse.quote_plus(_un)}:{urllib.parse.quote_plus(_pw)}@"
            conx = f"postgresql+psycopg2://{_unpw}{host_part}/{database}"
        elif _un:
            user_part = f"{urllib.parse.quote_plus(_un)}@"
            conx = f"postgresql+psycopg2://{user_part}{host_part}/{database}"
        else:
            conx = f"postgresql+psycopg2://@{host_part}/{database}"

        engine = create_engine(
            conx,
            executemany_mode="values_plus_batch",
            insertmanyvalues_page_size=5000,
            executemany_batch_page_size=500,
        )
        session = scoped_session(sessionmaker(bind=engine))
        super().__init__(name, conx, engine=engine, session=session)

    def _format_procedure_sql(self, procedure_name: str) -> str:
        return f"call {procedure_name};"

    def interop(self, insert_command: str) -> int:
        con = self.engine.raw_connection()
        cur = con.cursor()
        cur.execute(insert_command)
        result = cur.fetchone()
        con.commit()
        return int(result[0]) if result else -1

    def interop_returnind_id(self, insert_command: str) -> int:
        """Backward-compatible alias for interop()."""
        return self.interop(insert_command)
