"""A library with utilities for testing the Spanner database implementation."""
import os
import unittest

from typing import Optional

from absl.testing import absltest

from google.cloud import spanner_v1 as spanner_lib
from google.cloud import spanner_admin_database_v1
from google.cloud.spanner import Client, KeySet
from google.cloud.spanner_admin_database_v1.types import spanner_database_admin

from grr_response_server.databases import spanner_utils

OPERATION_TIMEOUT_SECONDS = 240

PROD_SCHEMA_SDL_PATH = "grr/server/grr_response_server/databases/spanner.sdl"
TEST_SCHEMA_SDL_PATH = "grr/server/grr_response_server/databases/spanner_test.sdl"

def _GetEnvironOrSkip(key):
  value = os.environ.get(key)
  if value is None:
    raise unittest.SkipTest("'%s' variable is not set" % key)
  return value

def _readSchemaFromFile(file_path):
    """Reads DDL statements from a file."""
    with open(file_path, 'r') as f:
        # Read the whole file and split by semicolon.
        # Filter out any empty strings resulting from split.
        ddl_statements = [stmt.strip() for stmt in f.read().split(';') if stmt.strip()]
    return ddl_statements

def Init(sdl_path: str) -> None:
  """Initializes the Spanner testing environment.

  This must be called only once per test process. A `setUpModule` method is
  a perfect place for it.

  """
  global _TEST_DB

  if _TEST_DB is not None:
    raise AssertionError("Spanner test library already initialized")

  project_id = _GetEnvironOrSkip("PROJECT_ID")
  instance_id = _GetEnvironOrSkip("SPANNER_TEST_INSTANCE")
  database_id = _GetEnvironOrSkip("SPANNER_TEST_DATABASE")

  spanner_client = Client(project_id)
  database_admin_api = spanner_client.database_admin_api

  ddl_statements = _readSchemaFromFile(sdl_path)

  request = spanner_database_admin.CreateDatabaseRequest(
    parent=database_admin_api.instance_path(spanner_client.project, instance_id),
    create_statement=f"CREATE DATABASE `{database_id}`",
    extra_statements=ddl_statements
  )

  operation = database_admin_api.create_database(request=request)

  print("Waiting for operation to complete...")
  database = operation.result(OPERATION_TIMEOUT_SECONDS)

  print(
    "Created database {} on instance {}".format(
            database.name,
            database_admin_api.instance_path(spanner_client.project, instance_id),
    )
  )

  instance = spanner_client.instance(instance_id)
  _TEST_DB = instance.database(database_id)
 

def TearDown() -> None:
  """Tears down the Spanner testing environment.

  This must be called once per process after all the tests. A `tearDownModule`
  is a perfect place for it.
  """
  if _TEST_DB is not None:
    # Create a client
    _TEST_DB.drop()


def CreateTestDatabase() -> spanner_lib.database:
  """Creates an empty test spanner database.

  Returns:
    A PySpanner instance pointing to the created database.
  """
  #if _TEST_DB is None:
  #  raise AssertionError("Spanner test database not initialized")

  db = spanner_utils.Database(_TEST_DB)

  query = """
  SELECT t.table_name
    FROM information_schema.tables AS t
   WHERE t.table_catalog = ""
     AND t.table_schema = ""
   ORDER BY t.table_name ASC
  """

  table_names = set()
  for (table_name,) in db.Query(query):
    table_names.add(table_name)

  query = """
  SELECT v.table_name
    FROM information_schema.views AS v
   WHERE v.table_catalog = ""
     AND v.table_schema = ""
   ORDER BY v.table_name ASC
  """
  view_names = set()
  for (view_name,) in db.Query(query):
    view_names.add(view_name)

  # `table_names` is a superset of `view_names` (since the `VIEWS` table is,
  # well, just a view to the `TABLES` table [1]). Since deleting from views
  # makes no sense, we have to exclude them from the tables we want to clean.
  table_names -= view_names
  
  keyset = KeySet(all_=True)

  with _TEST_DB.batch() as batch:
    # Deletes sample data from all tables in the given database.
    for table_name in table_names:
      batch.delete(table_name, keyset)

  return _TEST_DB

_TEST_DB: spanner_lib.database = None