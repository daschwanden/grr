import queue

from absl.testing import absltest

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.rdfvalues import mig_protodict
from grr_response_core.lib.rdfvalues import protodict as rdf_protodict
from grr_response_proto import objects_pb2

from grr_response_server.databases import db_message_handler_test
from grr_response_server.databases import spanner_test_lib


def setUpModule() -> None:
  spanner_test_lib.Init(spanner_test_lib.PROD_SCHEMA_SDL_PATH, True)


def tearDownModule() -> None:
  spanner_test_lib.TearDown()


class SpannerDatabaseHandlerTest(spanner_test_lib.TestCase
):
  def setUp(self):
    super().setUp()

  def testMessageHandlerRequests(self):

    requests = []
    for i in range(5):
      emb = mig_protodict.ToProtoEmbeddedRDFValue(
          rdf_protodict.EmbeddedRDFValue(rdfvalue.RDFInteger(i))
      )
      requests.append(
          objects_pb2.MessageHandlerRequest(
              client_id="C.1000000000000000",
              handler_name="Testhandler",
              request_id=i * 100,
              request=emb,
          )
      )

    self.db.WriteMessageHandlerRequests(requests)

    read = self.db.ReadMessageHandlerRequests()
    self.assertLen(read, 5)

    self.db.DeleteMessageHandlerRequests(read[:2])
    self.db.DeleteMessageHandlerRequests(read[4:5])
    
    for r in read:
      self.assertTrue(r.timestamp)
      r.ClearField("timestamp")
      self.assertTrue(r.ack_id)
      r.ClearField("ack_id")
    
    self.assertCountEqual(read, requests)

    read = self.db.ReadMessageHandlerRequests()
    self.assertLen(read, 2)
    self.db.DeleteMessageHandlerRequests(read)
    
    for r in read:
      self.assertTrue(r.timestamp)
      r.ClearField("timestamp")
      self.assertTrue(r.ack_id)
      r.ClearField("ack_id")

    self.assertCountEqual(requests[2:4], read)


if __name__ == "__main__":
  absltest.main()