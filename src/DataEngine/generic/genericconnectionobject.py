from ..base import BaseRdbmsConnectionObject


class GenericConnectionObject(BaseRdbmsConnectionObject):
    """Generic RDBMS connection wrapper for any database supported by SQLAlchemy.

    Allows callers to supply a custom or pre-formatted SQLAlchemy connection URI
    directly (e.g. SQLite, Snowflake, DuckDB, CockroachDB, or advanced connections
    with custom SSL certificates, Kerberos options, or query parameters).
    """

    def __init__(self, **kwargs):
        name = kwargs["name"]
        conx = (
            kwargs.get("connection")
            or kwargs.get("connection_string")
            or kwargs.get("url")
        )
        if not conx:
            raise ValueError(
                f"GenericConnectionObject '{name}' requires 'connection', "
                "'connection_string', or 'url' containing a valid SQLAlchemy URI."
            )

        engine_kwargs = kwargs.get("engine_kwargs") or {}
        super().__init__(name, str(conx), **engine_kwargs)
