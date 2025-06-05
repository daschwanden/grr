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


class SpannerDatabaseHandlerTest(spanner_test_lib.TestCase):
  def setUp(self):
    super().setUp()

  def testMessageHandlerRequests(self):

    ########################
    # Read / Write tests
    ########################
    requests = []
    for i in range(5):
      emb = mig_protodict.ToProtoEmbeddedRDFValue(
          rdf_protodict.EmbeddedRDFValue(rdfvalue.RDFInteger(i))
      )
      requests.append(
          objects_pb2.MessageHandlerRequest(
              client_id="C.1000000000000000",
              handler_name="Testhandler 0",
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

    ########################
    # Lease Management tests
    ########################

    requests = []
    for i in range(10):
      emb = mig_protodict.ToProtoEmbeddedRDFValue(
          rdf_protodict.EmbeddedRDFValue(rdfvalue.RDFInteger(i))
      )
      requests.append(
          objects_pb2.MessageHandlerRequest(
              client_id="C.1000000000000001",
              handler_name="Testhandler 1",
              request_id=i * 100,
              request=emb,
          )
      )

    lease_time = rdfvalue.Duration.From(5, rdfvalue.MINUTES)

    leased = queue.Queue()
    self.db.RegisterMessageHandler(leased.put, lease_time, limit=10)

    self.db.WriteMessageHandlerRequests(requests)

    got = []
    while len(got) < 10:
      try:
        l = leased.get(True, timeout=6)
      except queue.Empty:
        self.fail(
            "Timed out waiting for messages, expected 10, got %d" % len(got)
        )
      self.assertLessEqual(len(l), 10)
      for m in l:
        self.assertEqual(m.leased_by, utils.ProcessIdString())
        self.assertGreater(m.leased_until, rdfvalue.RDFDatetime.Now())
        self.assertLess(m.timestamp, rdfvalue.RDFDatetime.Now())
      got += l
    self.db.DeleteMessageHandlerRequests(got)

    got.sort(key=lambda req: req.request_id)
    for m in got:
      m.ClearField("leased_by")
      m.ClearField("leased_until")
      m.ClearField("timestamp")
      m.ClearField("ack_id")
    self.assertEqual(requests, got)

    self.db.UnregisterMessageHandler()

if __name__ == "__main__":
  absltest.main()