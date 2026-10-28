import pytest
from unittest.mock import MagicMock
from DataEngine.generic.genericconnectionobject import GenericConnectionObject


class TestGenericConnectionObject:
    def test_init_with_connection_string(self, mocker):
        mock_engine = mocker.patch("DataEngine.base.create_engine")
        mocker.patch("DataEngine.base.scoped_session")
        mocker.patch("DataEngine.base.sessionmaker")

        obj = GenericConnectionObject(name="custom", connection="sqlite:///:memory:")
        assert obj.name == "custom"
        assert obj.connection == "sqlite:///:memory:"
        mock_engine.assert_called_once_with("sqlite:///:memory:")

    def test_init_with_url_alias(self, mocker):
        mock_engine = mocker.patch("DataEngine.base.create_engine")
        mocker.patch("DataEngine.base.scoped_session")
        mocker.patch("DataEngine.base.sessionmaker")

        obj = GenericConnectionObject(name="custom_url", url="duckdb:///my.duckdb")
        assert obj.connection == "duckdb:///my.duckdb"

    def test_init_missing_connection_raises(self):
        with pytest.raises(ValueError, match="requires 'connection'"):
            GenericConnectionObject(name="broken")

    def test_passes_engine_kwargs(self, mocker):
        mock_engine = mocker.patch("DataEngine.base.create_engine")
        mocker.patch("DataEngine.base.scoped_session")
        mocker.patch("DataEngine.base.sessionmaker")

        GenericConnectionObject(
            name="pool_test",
            connection="postgresql://localhost/db",
            engine_kwargs={"pool_size": 20, "echo": True},
        )
        mock_engine.assert_called_once_with("postgresql://localhost/db", pool_size=20, echo=True)
