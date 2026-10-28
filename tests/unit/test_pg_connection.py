import pytest

from DataEngine.postgres.pgconnectionobject import PgConnectionObject


class TestPgConnectionObject:
    def _make(self, mocker, **overrides):
        mock_engine = mocker.MagicMock()
        mock_engine.url.host = overrides.get("server", "pgserver")
        mock_engine.url.database = overrides.get("database", "pgdb")
        mocker.patch("DataEngine.postgres.pgconnectionobject.create_engine", return_value=mock_engine)
        mocker.patch("DataEngine.postgres.pgconnectionobject.scoped_session")
        mocker.patch("DataEngine.postgres.pgconnectionobject.sessionmaker")
        kwargs = dict(name="pg", server="pgserver", database="pgdb", UN="user", PW="pass")
        kwargs.update(overrides)
        return PgConnectionObject(**kwargs)

    def test_connection_string_uses_psycopg2_scheme(self, mocker):
        obj = self._make(mocker)
        assert obj.connection.startswith("postgresql+psycopg2://")

    def test_connection_string_contains_server_and_database(self, mocker):
        obj = self._make(mocker)
        assert "@pgserver/pgdb" in obj.connection

    def test_connection_string_contains_credentials(self, mocker):
        obj = self._make(mocker)
        assert "user:" in obj.connection
        assert "@pgserver" in obj.connection

    def test_repr(self, mocker):
        obj = self._make(mocker)
        assert repr(obj) == "PgConnectionObject:pg = pgserver.pgdb"

    def test_name_is_stored(self, mocker):
        obj = self._make(mocker, name="analytics")
        assert obj.name == "analytics"

    def test_trusted_uses_gssapi_kerberos(self, mocker):
        obj = self._make(mocker, trusted="yes", UN="", PW="")
        assert obj.connection.startswith("postgresql+psycopg2://@pgserver/pgdb?gssencmode=prefer")

    def test_un_without_pw_omits_password(self, mocker):
        obj = self._make(mocker, trusted=False, UN="app_user", PW="")
        assert obj.connection == "postgresql+psycopg2://app_user@pgserver/pgdb"
