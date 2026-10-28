import pytest
import pandas as pd
from unittest.mock import MagicMock
from DataEngine.base import BaseRdbmsConnectionObject


class TestBaseRdbmsConnectionObject:
    def _make(self):
        engine = MagicMock()
        session = MagicMock()
        return BaseRdbmsConnectionObject("test_db", "sqlite:///:memory:", engine=engine, session=session)

    def test_init_stores_attributes(self):
        obj = self._make()
        assert obj.name == "test_db"
        assert obj.connection == "sqlite:///:memory:"
        assert obj.engine is not None
        assert obj.session is not None

    def test_getConnection_calls_engine_connect(self):
        obj = self._make()
        obj.getConnection()
        obj.engine.connect.assert_called_once()

    def test_getStreamingConnection_enables_stream_results(self):
        obj = self._make()
        conn = obj.engine.connect.return_value
        obj.getStreamingConnection()
        conn.execution_options.assert_called_once_with(stream_results=True)

    def test_query_fetches_all_and_commits(self):
        obj = self._make()
        mock_conn = MagicMock()
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [("row1",), ("row2",)]
        mock_conn.execute.return_value = mock_result
        obj.engine.connect.return_value.__enter__.return_value = mock_conn

        results = obj.query("SELECT 1")
        assert results == [("row1",), ("row2",)]
        mock_conn.commit.assert_called_once()

    def test_execute_runs_and_commits(self):
        obj = self._make()
        mock_conn = MagicMock()
        obj.engine.connect.return_value.__enter__.return_value = mock_conn

        obj.execute("UPDATE table SET x = 1")
        mock_conn.commit.assert_called_once()

    def test_executeProcedure_executes_formatted_sql(self):
        obj = self._make()
        mock_conn = MagicMock()
        obj.engine.connect.return_value.__enter__.return_value = mock_conn

        obj.executeProcedure("my_sp")
        mock_conn.commit.assert_called_once()

    def test_truncateTable_executes_truncate(self):
        obj = self._make()
        mock_conn = MagicMock()
        obj.engine.connect.return_value.__enter__.return_value = mock_conn

        obj.truncateTable("dbo", "MyTable")
        mock_conn.commit.assert_called_once()

    def test_truncateTable_without_schema(self):
        obj = self._make()
        mock_conn = MagicMock()
        obj.engine.connect.return_value.__enter__.return_value = mock_conn

        obj.truncateTable(None, "MyTable")
        mock_conn.commit.assert_called_once()
