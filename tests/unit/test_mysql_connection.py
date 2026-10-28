import pytest
from DataEngine.mysql.mysqlconnectionobject import MysqlConnectionObject


class TestMysqlConnectionObject:
    def _make(self, mocker, **overrides):
        mock_engine = mocker.MagicMock()
        mock_engine.url.host = overrides.get("server", "mysqlserver")
        mock_engine.url.database = overrides.get("database", "mysqldb")
        mocker.patch("DataEngine.mysql.mysqlconnectionobject.create_engine", return_value=mock_engine)
        mocker.patch("DataEngine.mysql.mysqlconnectionobject.scoped_session")
        mocker.patch("DataEngine.mysql.mysqlconnectionobject.sessionmaker")
        kwargs = dict(name="mysql_conn", server="mysqlserver", database="mysqldb", UN="root", PW="secret")
        kwargs.update(overrides)
        return MysqlConnectionObject(**kwargs)

    def test_connection_string_uses_pymysql_scheme(self, mocker):
        obj = self._make(mocker)
        assert obj.connection.startswith("mysql+pymysql://")

    def test_connection_string_contains_server_database_and_port(self, mocker):
        obj = self._make(mocker, port=3307)
        assert "@mysqlserver:3307/mysqldb?charset=utf8mb4" in obj.connection

    def test_connection_string_contains_credentials(self, mocker):
        obj = self._make(mocker)
        assert "root:secret@" in obj.connection

    def test_connection_string_without_credentials(self, mocker):
        obj = self._make(mocker, UN="", PW="")
        assert "mysql+pymysql://@mysqlserver:3306/mysqldb" in obj.connection

    def test_trusted_windows_auth(self, mocker):
        obj = self._make(mocker, trusted="yes", UN="", PW="")
        assert "mysql+pymysql://@mysqlserver:3306/mysqldb" in obj.connection

    def test_repr(self, mocker):
        obj = self._make(mocker)
        assert repr(obj) == "MysqlConnectionObject:mysql_conn = mysqlserver.mysqldb"

    def test_name_is_stored(self, mocker):
        obj = self._make(mocker, name="warehouse")
        assert obj.name == "warehouse"

    def test_procedure_formatting(self, mocker):
        obj = self._make(mocker)
        assert obj._format_procedure_sql("sp_get_users") == "call sp_get_users;"
