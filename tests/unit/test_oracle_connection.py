import pytest
from DataEngine.oracle.oracleconnectionobject import OracleConnectionObject


class TestOracleConnectionObject:
    def _make(self, mocker, **overrides):
        mock_engine = mocker.MagicMock()
        mock_engine.url.host = overrides.get("server", "oraserver")
        mock_engine.url.database = overrides.get("database", "oradb")
        mocker.patch("DataEngine.oracle.oracleconnectionobject.create_engine", return_value=mock_engine)
        mocker.patch("DataEngine.oracle.oracleconnectionobject.scoped_session")
        mocker.patch("DataEngine.oracle.oracleconnectionobject.sessionmaker")
        kwargs = dict(name="ora_conn", server="oraserver", database="oradb", UN="system", PW="manager")
        kwargs.update(overrides)
        return OracleConnectionObject(**kwargs)

    def test_connection_string_uses_oracledb_scheme(self, mocker):
        obj = self._make(mocker)
        assert obj.connection.startswith("oracle+oracledb://")

    def test_connection_string_contains_service_name(self, mocker):
        obj = self._make(mocker, service_name="XEPDB1", port=1522)
        assert "@oraserver:1522/?service_name=XEPDB1" in obj.connection

    def test_connection_string_contains_credentials(self, mocker):
        obj = self._make(mocker)
        assert "system:manager@" in obj.connection

    def test_repr(self, mocker):
        obj = self._make(mocker)
        assert repr(obj) == "OracleConnectionObject:ora_conn = oraserver.oradb"

    def test_name_is_stored(self, mocker):
        obj = self._make(mocker, name="finance")
        assert obj.name == "finance"

    def test_procedure_formatting(self, mocker):
        obj = self._make(mocker)
        assert obj._format_procedure_sql("pkg_audit.proc_run") == "begin pkg_audit.proc_run; end;"

    def test_trusted_uses_wallet_external_auth(self, mocker):
        obj = self._make(mocker, trusted="yes", UN="", PW="")
        assert "oracle+oracledb:///@oraserver:1521/?service_name=oradb" in obj.connection
