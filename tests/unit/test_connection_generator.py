import json
import os

import pytest

import DataEngine


_MSSQL_DOC = {
    "type": "mssql",
    "server": "srv",
    "database": "db",
    "UN": "",
    "PW": "",
    "trusted": "yes",
}


def _doc(**overrides):
    return {**_MSSQL_DOC, **overrides}


@pytest.fixture()
def registries():
    """Isolates the module-level registries.

    connectionGenerator() rebinds alchemyConnections (it does not mutate it), so
    the attributes are saved and restored rather than patched in place.
    """
    saved_connections = DataEngine.alchemyConnections
    saved_objects = DataEngine.alchemyObjects
    DataEngine.alchemyConnections = {}
    DataEngine.alchemyObjects = {}
    yield DataEngine
    DataEngine.alchemyConnections = saved_connections
    DataEngine.alchemyObjects = saved_objects


@pytest.fixture()
def mock_sql_object(mocker):
    """Stops connectionGenerator from building a real engine."""
    return mocker.patch("DataEngine.SqlConnectionObject")


# ---------------------------------------------------------------------------
# connectionGenerator — programmatic mode (a dict is supplied)
# ---------------------------------------------------------------------------

class TestConnectionGeneratorWithSuppliedDict:
    def test_builds_connections_from_supplied_dict(self, registries, mock_sql_object):
        DataEngine.connectionGenerator({"cli": _doc(server="cli_srv")})

        assert "cli" in DataEngine.alchemyObjects
        assert mock_sql_object.call_args.kwargs["server"] == "cli_srv"

    def test_supplied_dict_takes_precedence_over_existing_connections(
        self, registries, mock_sql_object
    ):
        # Regression: the argument must win over whatever import-time
        # auto-initialisation already left in alchemyConnections.
        DataEngine.alchemyConnections = {"from_env": _doc(server="env_srv")}

        DataEngine.connectionGenerator({"from_caller": _doc(server="caller_srv")})

        assert "from_caller" in DataEngine.alchemyObjects
        assert "from_env" not in DataEngine.alchemyObjects
        assert mock_sql_object.call_args.kwargs["server"] == "caller_srv"

    def test_does_not_read_env_file_when_dict_supplied(
        self, registries, mock_sql_object, mocker
    ):
        load_dotenv = mocker.patch("DataEngine.load_dotenv")

        DataEngine.connectionGenerator({"cli": _doc()})

        load_dotenv.assert_not_called()

    def test_supplied_credentials_do_not_enter_the_saveable_registry(
        self, registries, mock_sql_object
    ):
        # alchemyConnections is what saveConnectionStrings() writes to
        # database.env in plaintext. A credential passed in memory must not
        # become persistable as a side effect of building the connection.
        DataEngine.connectionGenerator({"cli": _doc(trusted="no", UN="u", PW="s3cret")})

        assert "cli" not in DataEngine.alchemyConnections


# ---------------------------------------------------------------------------
# connectionGenerator — type dispatch
# ---------------------------------------------------------------------------

class TestConnectionGeneratorTypeDispatch:
    def test_mssql_builds_a_sql_connection_object(self, registries, mock_sql_object):
        DataEngine.connectionGenerator({"a": _doc(type="mssql")})
        mock_sql_object.assert_called_once()

    def test_postgres_builds_a_pg_connection_object(self, registries, mocker):
        mock_pg = mocker.patch("DataEngine.PgConnectionObject")
        DataEngine.connectionGenerator({"a": _doc(type="postgres")})
        mock_pg.assert_called_once()

    def test_mongo_builds_a_mongo_connection_object(self, registries, mocker):
        mock_mongo = mocker.patch("DataEngine.MongoConnectionObject")
        DataEngine.connectionGenerator({"a": _doc(type="mongo")})
        mock_mongo.assert_called_once()

    def test_mysql_builds_a_mysql_connection_object(self, registries, mocker):
        mock_mysql = mocker.patch("DataEngine.MysqlConnectionObject")
        DataEngine.connectionGenerator({"a": _doc(type="mysql")})
        mock_mysql.assert_called_once()

    def test_mariadb_builds_a_mysql_connection_object(self, registries, mocker):
        mock_mysql = mocker.patch("DataEngine.MysqlConnectionObject")
        DataEngine.connectionGenerator({"a": _doc(type="mariadb")})
        mock_mysql.assert_called_once()

    def test_oracle_builds_an_oracle_connection_object(self, registries, mocker):
        mock_oracle = mocker.patch("DataEngine.OracleConnectionObject")
        DataEngine.connectionGenerator({"a": _doc(type="oracle")})
        mock_oracle.assert_called_once()

    def test_generic_builds_a_generic_connection_object(self, registries, mocker):
        mock_generic = mocker.patch("DataEngine.GenericConnectionObject")
        DataEngine.connectionGenerator({"custom": {"type": "generic", "connection": "sqlite:///:memory:"}})
        mock_generic.assert_called_once_with(name="custom", connection="sqlite:///:memory:", engine_kwargs={})

    def test_unrecognised_type_raises(self, registries, mock_sql_object):
        # Silently building nothing is the same class of failure as building the
        # wrong thing: the caller gets no connection and no explanation.
        with pytest.raises(ValueError):
            DataEngine.connectionGenerator({"legacy": _doc(type="unsupported_db")})

    def test_unrecognised_type_error_names_the_type_and_the_connection(
        self, registries, mock_sql_object
    ):
        with pytest.raises(ValueError, match="unsupported_db"):
            DataEngine.connectionGenerator({"legacy": _doc(type="unsupported_db")})

        with pytest.raises(ValueError, match="legacy"):
            DataEngine.connectionGenerator({"legacy": _doc(type="unsupported_db")})


# ---------------------------------------------------------------------------
# connectionGenerator — optional keys in a connection document
# ---------------------------------------------------------------------------

class TestConnectionGeneratorOptionalKeys:
    def test_omitted_credentials_default_to_empty_strings(self, registries, mock_sql_object):
        # Windows auth makes UN/PW meaningless — a hand-built dict should not
        # have to carry them just to satisfy a lookup.
        DataEngine.connectionGenerator(
            {"win": {"type": "mssql", "server": "srv", "database": "db", "trusted": "yes"}}
        )

        assert mock_sql_object.call_args.kwargs["UN"] == ""
        assert mock_sql_object.call_args.kwargs["PW"] == ""

    def test_omitted_trusted_defaults_to_no(self, registries, mock_sql_object):
        DataEngine.connectionGenerator(
            {"sql": {"type": "mssql", "server": "srv", "database": "db", "UN": "u", "PW": "p"}}
        )

        assert mock_sql_object.call_args.kwargs["trusted"] == "no"

    def test_minimal_document_builds_a_connection(self, registries, mock_sql_object):
        DataEngine.connectionGenerator(
            {"min": {"type": "mssql", "server": "srv", "database": "db"}}
        )

        assert "min" in DataEngine.alchemyObjects

    def test_postgres_document_omitting_credentials(self, registries, mocker):
        mock_pg = mocker.patch("DataEngine.PgConnectionObject")

        DataEngine.connectionGenerator(
            {"pg": {"type": "postgres", "server": "srv", "database": "db"}}
        )

        assert mock_pg.call_args.kwargs["UN"] == ""
        assert mock_pg.call_args.kwargs["PW"] == ""

    @pytest.mark.parametrize("missing", ["type", "server", "database"])
    def test_missing_required_key_still_raises(self, registries, mock_sql_object, missing):
        doc = _doc()
        del doc[missing]

        with pytest.raises(KeyError):
            DataEngine.connectionGenerator({"broken": doc})


# ---------------------------------------------------------------------------
# connectionGenerator — declarative mode (no argument)
# ---------------------------------------------------------------------------

class TestConnectionGeneratorFromEnvFile:
    def test_no_argument_loads_connections_from_env_file(
        self, registries, mock_sql_object, mocker
    ):
        mocker.patch("DataEngine.load_dotenv")
        mocker.patch.dict(
            os.environ, {"databases": json.dumps({"main": _doc(server="env_srv")})}
        )

        DataEngine.connectionGenerator()

        assert "main" in DataEngine.alchemyObjects
        assert mock_sql_object.call_args.kwargs["server"] == "env_srv"

    def test_no_argument_populates_the_saveable_registry(
        self, registries, mock_sql_object, mocker
    ):
        mocker.patch("DataEngine.load_dotenv")
        mocker.patch.dict(
            os.environ, {"databases": json.dumps({"main": _doc()})}
        )

        DataEngine.connectionGenerator()

        assert "main" in DataEngine.alchemyConnections


# ---------------------------------------------------------------------------
# Password resolution — file:, ${ENV}, prompt, and literal
# ---------------------------------------------------------------------------

class TestPasswordResolution:
    def test_file_reference_reads_from_disk(self, registries, mock_sql_object, tmp_path):
        pwd_file = tmp_path / "db.pwd"
        pwd_file.write_text("s3cret_from_file\n")

        DataEngine.connectionGenerator(
            {"app": _doc(trusted="no", UN="user", PW=f"file:{pwd_file}")}
        )

        assert mock_sql_object.call_args.kwargs["PW"] == "s3cret_from_file"

    def test_missing_file_reference_raises_file_not_found(self, registries, mock_sql_object, tmp_path):
        missing = tmp_path / "nonexistent.pwd"
        with pytest.raises(FileNotFoundError, match="Password file not found"):
            DataEngine.connectionGenerator(
                {"app": _doc(trusted="no", UN="user", PW=f"file:{missing}")}
            )

    def test_env_var_reference_reads_from_environ(self, registries, mock_sql_object, monkeypatch):
        monkeypatch.setenv("APP_DB_PASSWORD", "env_secret_123")

        DataEngine.connectionGenerator(
            {"app": _doc(trusted="no", UN="user", PW="${APP_DB_PASSWORD}")}
        )

        assert mock_sql_object.call_args.kwargs["PW"] == "env_secret_123"

    def test_prompt_with_interactive_tty_calls_getpass(self, registries, mock_sql_object, mocker):
        mocker.patch("sys.stdin.isatty", return_value=True)
        mock_getpass = mocker.patch("getpass.getpass", return_value="typed_secret")

        DataEngine.connectionGenerator(
            {"app": _doc(trusted="no", UN="admin", PW="prompt")}
        )

        mock_getpass.assert_called_once()
        assert mock_sql_object.call_args.kwargs["PW"] == "typed_secret"

    def test_prompt_without_tty_raises_runtime_error(self, registries, mock_sql_object, mocker):
        mocker.patch("sys.stdin.isatty", return_value=False)

        with pytest.raises(RuntimeError, match="no interactive terminal"):
            DataEngine.connectionGenerator(
                {"app": _doc(trusted="no", UN="admin", PW="prompt")}
            )

    def test_literal_password_preserved(self, registries, mock_sql_object):
        DataEngine.connectionGenerator(
            {"app": _doc(trusted="no", UN="user", PW="regular_password")}
        )

        assert mock_sql_object.call_args.kwargs["PW"] == "regular_password"
