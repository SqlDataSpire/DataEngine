import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from ..base import BaseRdbmsConnectionObject


class OracleConnectionObject(BaseRdbmsConnectionObject):
    """Oracle connection wrapper using the python-oracledb driver in default Thin mode."""

    def __init__(self, **kwargs):
        name = kwargs["name"]
        server = kwargs["server"]
        database = kwargs.get("database", "") or ""
        service_name = kwargs.get("service_name") or database
        un = kwargs.get("UN", "") or ""
        pw = kwargs.get("PW", "") or ""
        port = kwargs.get("port", 1521) or 1521
        trusted = kwargs.get("trusted", False)
        if isinstance(trusted, str):
            trusted = trusted.strip().lower() == "yes"

        if trusted or (not un and not pw):
            # Oracle External Authentication / Oracle Wallet syntax (/@)
            user_pw = "/@"
        elif un and pw:
            user_pw = f"{urllib.parse.quote_plus(str(un))}:{urllib.parse.quote_plus(str(pw))}@"
        elif un:
            user_pw = f"{urllib.parse.quote_plus(str(un))}@"
        else:
            user_pw = "/@"

        if service_name:
            conx = f"oracle+oracledb://{user_pw}{server}:{port}/?service_name={urllib.parse.quote_plus(str(service_name))}"
        else:
            conx = f"oracle+oracledb://{user_pw}{server}:{port}"

        engine = create_engine(conx)
        session = scoped_session(sessionmaker(bind=engine))
        super().__init__(name, conx, engine=engine, session=session)

    def _format_procedure_sql(self, procedure_name: str) -> str:
        return f"begin {procedure_name}; end;"
