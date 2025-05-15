#!/usr/bin/env python
"""A module with flow methods of the Spanner database implementation."""

import dataclasses
import datetime
import logging
from typing import Any, Callable, Collection, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union

from grr_response_core.lib import rdfvalue
from grr_response_core.lib import utils
from grr_response_core.lib.util import collection
from grr_response_core.stats import metrics
from grr_response_proto import flows_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_clients
from grr_response_server.databases import spanner_utils
from grr_response_server.models import hunts as models_hunts
from grr_response_proto import rrg_pb2

class FlowsMixin:
  """A Spanner database mixin with implementation of flow methods."""

  db: spanner_utils.Database
  _write_rows_batch_size: int


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowObject(
      self,
      flow_obj: flows_pb2.Flow,
      allow_update: bool = True,
  ) -> None:
    """Writes a flow object to the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadFlowObject(
      self,
      client_id: str,
      flow_id: str,
  ) -> flows_pb2.Flow:
    """Reads a flow object from the database."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAllFlowObjects(
      self,
      client_id: Optional[str] = None,
      parent_flow_id: Optional[str] = None,
      min_create_time: Optional[rdfvalue.RDFDatetime] = None,
      max_create_time: Optional[rdfvalue.RDFDatetime] = None,
      include_child_flows: bool = True,
      not_created_by: Optional[Iterable[str]] = None,
  ) -> Sequence[flows_pb2.Flow]:
    """Returns all flow objects that meet the specified conditions."""
    result = []

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateFlow(
      self,
      client_id: str,
      flow_id: str,
      flow_obj: Union[
          flows_pb2.Flow, db.Database.UNCHANGED_TYPE
      ] = db.Database.UNCHANGED,
      flow_state: Union[
          flows_pb2.Flow.FlowState.ValueType, db.Database.UNCHANGED_TYPE
      ] = db.Database.UNCHANGED,
      client_crash_info: Union[
          jobs_pb2.ClientCrash, db.Database.UNCHANGED_TYPE
      ] = db.Database.UNCHANGED,
      processing_on: Optional[
          Union[str, db.Database.UNCHANGED_TYPE]
      ] = db.Database.UNCHANGED,
      processing_since: Optional[
          Union[rdfvalue.RDFDatetime, db.Database.UNCHANGED_TYPE]
      ] = db.Database.UNCHANGED,
      processing_deadline: Optional[
          Union[rdfvalue.RDFDatetime, db.Database.UNCHANGED_TYPE]
      ] = db.Database.UNCHANGED,
  ) -> None:
    """Updates flow objects in the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowResults(self, results: Sequence[flows_pb2.FlowResult]) -> None:
    """Writes flow results for a given flow."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowErrors(self, errors: Sequence[flows_pb2.FlowError]) -> None:
    """Writes flow errors for a given flow."""



  def ReadFlowResults(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowResult]:
    """Reads flow results of a given flow using given query options."""
    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowError]:
    """Reads flow errors of a given flow using given query options."""

    return []

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountFlowResults(
      self,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    """Counts flow results of a given flow using given query options."""

    return 0

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountFlowErrors(
      self,
      client_id: str,
      flow_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    """Counts flow errors of a given flow using given query options."""

    return 0

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountFlowResultsByType(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow results grouped by result type."""

    query = """
    SELECT r.RdfType, COUNT(*)
    FROM FlowResults AS r
    WHERE r.ClientId = {client_id} AND r.FlowId = {flow_id}
    GROUP BY RdfType
    """

    result = {}

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountFlowErrorsByType(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow errors grouped by error type."""
    result = {}

    return result

  def _BuildFlowProcessingRequestWrites(
      self,
      mut: spanner_utils.Mutation,
      requests: Iterable[flows_pb2.FlowProcessingRequest],
  ) -> None:
    """Builds db writes for a list of FlowProcessingRequests."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowProcessingRequests(
      self,
      requests: Sequence[flows_pb2.FlowProcessingRequest],
  ) -> None:
    """Writes a list of flow processing requests to the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadFlowProcessingRequests(
      self,
  ) -> Sequence[flows_pb2.FlowProcessingRequest]:
    """Reads all flow processing requests from the database."""
    query = """
    SELECT t.Payload, t.CreationTime FROM FlowProcessingRequestsQueue AS t
    """

    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def AckFlowProcessingRequests(
      self, requests: Iterable[flows_pb2.FlowProcessingRequest]
  ) -> None:
    """Acknowledges and deletes flow processing requests."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteAllFlowProcessingRequests(self) -> None:
    """Deletes all flow processing requests from the database."""
    query = """
    DELETE FROM FlowProcessingRequestsQueue WHERE true
    """
    self.db.ParamExecute(query, {}, txn_tag="DeleteAllFlowProcessingRequests")

  def RegisterFlowProcessingHandler(
      self, handler: Callable[[flows_pb2.FlowProcessingRequest], None]
  ):
    """Registers a handler to receive flow processing messages."""


  def UnregisterFlowProcessingHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered flow processing handler."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowRequests(
      self,
      requests: Collection[flows_pb2.FlowRequest],
  ) -> None:
    """Writes a list of flow requests to the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowResponses(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
  ) -> None:
    """Writes Flow ressages and updates corresponding requests."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> None:
    """Deletes all requests and responses for a given flow from the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> Iterable[
      Tuple[
          flows_pb2.FlowRequest,
          Dict[
              int,
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ]
  ]:
    """Reads all requests and responses for a given flow from the database."""

    ret = []

    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteFlowRequests(
      self,
      requests: Sequence[flows_pb2.FlowRequest],
  ) -> None:
    """Deletes a list of flow requests from the database."""



  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadFlowRequests(
      self,
      client_id: str,
      flow_id: str,
  ) -> Dict[
      int,
      Tuple[
          flows_pb2.FlowRequest,
          List[
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ],
  ]:
    """Reads all requests for a flow that can be processed by the worker."""

    return {}

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateIncrementalFlowRequests(
      self,
      client_id: str,
      flow_id: str,
      next_response_id_updates: Mapping[int, int],
  ) -> None:
    """Updates next response ids of given requests."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowLogEntry(self, entry: flows_pb2.FlowLogEntry) -> None:
    """Writes a single flow log entry to the database."""

  def ReadFlowLogEntries(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    """Reads flow log entries of a given flow using given query options."""
    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountFlowLogEntries(self, client_id: str, flow_id: str) -> int:
    """Returns number of flow log entries of a given flow."""

    return 0

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      request_id: int,
      logs: Mapping[int, rrg_pb2.Log],
  ) -> None:
    """Writes new log entries for a particular action request."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadFlowRRGLogs(
      self,
      client_id: str,
      flow_id: str,
      offset: int,
      count: int,
  ) -> Sequence[rrg_pb2.Log]:
    """Reads log entries logged by actions issued by a particular flow."""

    return []

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowOutputPluginLogEntry(
      self,
      entry: flows_pb2.FlowOutputPluginLogEntry,
  ) -> None:
    """Writes a single output plugin log entry to the database.

    Args:
      entry: An output plugin flow entry to write.
    """


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads flow output plugin log entries."""
    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountFlowOutputPluginLogEntries(
      self,
      client_id: str,
      flow_id: str,
      output_plugin_id: str,
      with_type: Optional[
          flows_pb2.FlowOutputPluginLogEntry.LogEntryType.ValueType
      ] = None,
  ) -> int:
    """Returns the number of flow output plugin log entries of a given flow."""

    return 0

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteScheduledFlow(
      self,
      scheduled_flow: flows_pb2.ScheduledFlow,
  ) -> None:
    """Inserts or updates the ScheduledFlow in the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteScheduledFlow(
      self,
      client_id: str,
      creator: str,
      scheduled_flow_id: str,
  ) -> None:
    """Deletes the ScheduledFlow from the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ListScheduledFlows(
      self,
      client_id: str,
      creator: str,
  ) -> Sequence[flows_pb2.ScheduledFlow]:
    """Lists all ScheduledFlows for the client and creator."""

    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    """Writes a list of message handler requests to the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadMessageHandlerRequests(
      self,
  ) -> Sequence[objects_pb2.MessageHandlerRequest]:
    """Reads all message handler requests from the database."""

    results = []
    return results



  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    """Deletes a list of message handler requests from the database."""


  def RegisterMessageHandler(
      self,
      handler: Callable[[Sequence[objects_pb2.MessageHandlerRequest]], None],
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
  ) -> None:
    """Registers a message handler to receive batches of messages."""


  def UnregisterMessageHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered message handler."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def LeaseFlowForProcessing(
      self,
      client_id: str,
      flow_id: str,
      processing_time: rdfvalue.Duration,
  ) -> flows_pb2.Flow:
    """Marks a flow as being processed on this worker and returns it."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReleaseProcessedFlow(self, flow_obj: flows_pb2.Flow) -> bool:
    """Releases a flow that the worker was processing to the database."""

    return False
