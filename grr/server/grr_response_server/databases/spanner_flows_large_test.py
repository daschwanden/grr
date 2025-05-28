from absl.testing import absltest

from grr_response_server.databases import db_flows_test
from grr_response_server.databases import spanner_test_lib
from grr_response_server.databases import spanner_utils


def setUpModule() -> None:
  spanner_test_lib.Init(spanner_test_lib.PROD_SCHEMA_SDL_PATH, True)


def tearDownModule() -> None:
  spanner_test_lib.TearDown()


class SpannerDatabaseFlowsTest(
    db_flows_test.DatabaseLargeTestFlowMixin, spanner_test_lib.TestCase
):
  # Test methods are defined in the base mixin class.

  # To cleanup the database we use `DeleteWithPrefix` (to do multiple deletions
  # within a single mutation) but this method is super slow for cleaning up huge
  # amounts of data. Thus, for certain methods that populate the database with
  # a lot of rows we manually clean up using the `DELETE` DML statement which is
  # faster in such cases.

  def test40001RequestsCanBeWrittenAndRead(self):
    super().test40001RequestsCanBeWrittenAndRead()

    db: spanner_utils.Database = self.db.delegate.db  # pytype: disable=attribute-error
    db.ExecutePartitioned("DELETE FROM FlowRequests WHERE TRUE")

  def test40001ResponsesCanBeWrittenAndRead(self):
    super().test40001ResponsesCanBeWrittenAndRead()

    db: spanner_utils.Database = self.db.delegate.db  # pytype: disable=attribute-error
    db.ExecutePartitioned("DELETE FROM FlowResponses WHERE TRUE")

  def testWritesAndCounts40001FlowResults(self):
    super().testWritesAndCounts40001FlowResults()

    db: spanner_utils.Database = self.db.delegate.db  # pytype: disable=attribute-error
    db.ExecutePartitioned("DELETE FROM FlowResults WHERE TRUE")

  def testWritesAndCounts40001FlowErrors(self):
    super().testWritesAndCounts40001FlowErrors()

    db: spanner_utils.Database = self.db.delegate.db  # pytype: disable=attribute-error
    db.ExecutePartitioned("DELETE FROM FlowErrors WHERE TRUE")


if __name__ == "__main__":
  absltest.main()