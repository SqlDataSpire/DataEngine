import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from ..base import BaseRdbmsConnectionObject


class MysqlConnectionObject(BaseRdbmsConnectionObject):
    """MySQL and MariaDB connection wrapper using the pure-Python pymysql driver."""

    def __init__(self, **kwargs):
        name = kwargs["name"]
        server = kwargs["server"]
        database = kwargs["database"]
        un = kwargs.get("UN", "") or ""
        pw = kwargs.get("PW", "") or ""
        port = kwargs.get("port", 3306) or 3306
        charset = kwargs.get("charset", "utf8mb4") or "utf8mb4"
        trusted = kwargs.get("trusted", False)
        if isinstance(trusted, str):
            trusted = trusted.strip().lower() == "yes"

        if trusted:
            user_pw = "@"
        elif un and pw:
            user_pw = f"{urllib.parse.quote_plus(str(un))}:{urllib.parse.quote_plus(str(pw))}@"
        elif un:
            user_pw = f"{urllib.parse.quote_plus(str(un))}@"
        else:
            user_pw = "@"

        conx = f"mysql+pymysql://{user_pw}{server}:{port}/{database}?charset={charset}"

        engine = create_engine(conx)
        session = scoped_session(sessionmaker(bind=engine))
        super().__init__(name, conx, engine=engine, session=session)

    def _format_procedure_sql(self, procedure_name: str) -> str:
        return f"call {procedure_name};"

    def interop(self, insert_command: str) -> int:
        con = self.engine.raw_connection()
        cur = con.cursor()
        cur.execute(insert_command)
        cur.execute("SELECT LAST_INSERT_ID();")
        newid = cur.fetchone()
        con.commit()
        return int(newid[0]) if newid else -1
