from __future__ import annotations

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import scoped_session, sessionmaker


class BaseRdbmsConnectionObject:
    """Base class for relational database connection objects.

    Encapsulates the three primary SQLAlchemy/pandas interfaces:
      - self.connection: connection string / DSN
      - self.engine: SQLAlchemy Engine
      - self.session: SQLAlchemy scoped_session
    along with helper methods for executing queries, streaming results,
    and returning pandas DataFrames.
    """

    def __init__(
        self,
        name: str,
        connection_string: str,
        engine=None,
        session=None,
        **engine_kwargs,
    ):
        self.name = name
        self.connection = connection_string
        self.engine = (
            engine
            if engine is not None
            else create_engine(connection_string, **engine_kwargs)
        )
        self.session = (
            session
            if session is not None
            else scoped_session(sessionmaker(bind=self.engine))
        )

    def __repr__(self):
        host = getattr(self.engine.url, "host", "") or ""
        database = getattr(self.engine.url, "database", "") or ""
        return f"{self.__class__.__name__}:{self.name} = {host}.{database}"

    def getConnection(self):
        """Returns an active SQLAlchemy Connection."""
        return self.engine.connect()

    def getStreamingConnection(self):
        """Returns an active SQLAlchemy Connection with stream_results enabled."""
        return self.engine.connect().execution_options(stream_results=True)

    def _format_procedure_sql(self, procedure_name: str) -> str:
        """Formats the SQL statement used to invoke a stored procedure."""
        return f"call {procedure_name};"

    def executeProcedure(self, procedure_name: str, streaming: bool = False):
        con = self.getConnection if streaming is False else self.getStreamingConnection
        proc_sql = self._format_procedure_sql(procedure_name)
        with con() as tconn:
            try:
                tconn.execute(text(proc_sql))
                tconn.commit()
            except Exception as tctE:
                tconn.rollback()
                raise Exception(f"executeProcedure(): {tctE}")

    def truncateTable(self, schema: str | None, name: str):
        target = f"{schema}.{name}" if schema else name
        with self.getConnection() as tconn:
            try:
                tconn.execute(text(f"truncate table {target};"))
                tconn.commit()
            except Exception as tctE:
                tconn.rollback()
                raise Exception(f"truncateTable(): {tctE}")

    def query(self, query_text: str):
        statement = text(query_text)
        with self.getConnection() as con:
            results = con.execute(statement).fetchall()
            con.commit()
        return results

    def execute(self, non_result_query: str):
        statement = text(non_result_query)
        with self.getConnection() as con:
            con.execute(statement)
            con.commit()

    def queryStream(self, query_text: str):
        statement = text(query_text)
        with self.getStreamingConnection() as con:
            for item in con.execute(statement).fetchall():
                yield item
            con.commit()

    def getTable(self, query_text: str) -> pd.DataFrame:
        statement = text(query_text)
        with self.getConnection() as con:
            df = pd.read_sql(statement, con)
        return df

    def chunkTable(self, query_text: str, chunksize: int):
        statement = text(query_text)
        with self.getStreamingConnection() as con:
            for chunk in pd.read_sql(statement, con, chunksize=chunksize):
                yield chunk
