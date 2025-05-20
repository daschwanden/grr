from absl.testing import absltest

from grr_response_server.databases import db_blob_references_test
from grr_response_server.databases import spanner_test_lib


def setUpModule() -> None:
  spanner_test_lib.Init(spanner_test_lib.PROD_SCHEMA_SDL_PATH, True)


def tearDownModule() -> None:
  spanner_test_lib.TearDown()


class SpannerDatabaseBlobReferencesTest(
    db_blob_references_test.DatabaseTestBlobReferencesMixin,
    spanner_test_lib.TestCase,
):
  pass  # Test methods are defined in the base mixin class.


if __name__ == "__main__":
  absltest.main()