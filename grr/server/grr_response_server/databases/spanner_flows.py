#!/usr/bin/env python
"""A module with flow methods of the Spanner database implementation."""

import dataclasses
import datetime
import logging
from typing import Any, Callable, Collection, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union

from google.api_core.exceptions import AlreadyExists, NotFound
from google.cloud import spanner as spanner_lib

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


SPANNER_DELETE_FLOW_REQUESTS_FAILURES = metrics.Counter(
    name="spanner_delete_flow_requests_failures"
)

_MESSAGE_HANDLER_MAX_KEEPALIVE_SECONDS = 300
_MESSAGE_HANDLER_MAX_ACTIVE_CALLBACKS = 20

_MILLISECONDS = 1000
_SECONDS = 1000 * _MILLISECONDS

@dataclasses.dataclass(frozen=True)
class _FlowKey:
  """Unique key identifying a flow in helper methods."""

  client_id: str
  flow_id: str


@dataclasses.dataclass(frozen=True)
class _RequestKey:
  """Unique key identifying a flow request in helper methods."""

  client_id: str
  flow_id: str
  request_id: int


@dataclasses.dataclass(frozen=True)
class _ResponseKey:
  """Unique key identifying a flow response in helper methods."""

  client_id: str
  flow_id: str
  request_id: int
  response_id: int


_UNCHANGED = db.Database.UNCHANGED
_UNCHANGED_TYPE = db.Database.UNCHANGED_TYPE


def _BuildReadFlowResultsErrorsConditions(
    table_name: str,
    client_id: str,
    flow_id: str,
    offset: int,
    count: int,
    with_tag: Optional[str] = None,
    with_type: Optional[str] = None,
    with_substring: Optional[str] = None,
) -> tuple[str, Mapping[str, Any]]:
  """Builds query string and params for results/errors reading queries."""
  params = {}

  query = f"""
  SELECT t.Payload, t.RdfType, t.CreationTime, t.Tag, t.HuntId
  FROM {table_name} AS t
  """

  query += """
  WHERE t.ClientId = {client_id} AND t.FlowId = {flow_id}
  """

  params["client_id"] = spanner_clients.IntClientID(client_id)
  params["flow_id"] = IntFlowID(flow_id)

  if with_tag is not None:
    query += " AND t.Tag = {tag} "
    params["tag"] = with_tag

  if with_type is not None:
    query += " AND t.RdfType = {type}"
    params["type"] = with_type

  if with_substring is not None:
    query += """
    AND STRPOS(SAFE_CONVERT_BYTES_TO_STRING(t.Payload.value), {substring}) != 0
    """
    params["substring"] = with_substring

  query += """
  ORDER BY t.CreationTime ASC LIMIT {count} OFFSET {offset}
  """
  params["offset"] = offset
  params["count"] = count

  return query, params


def _BuildCountFlowResultsErrorsConditions(
    table_name: str,
    client_id: str,
    flow_id: str,
    with_tag: Optional[str] = None,
    with_type: Optional[str] = None,
) -> tuple[str, Mapping[str, Any]]:
  """Builds query string and params for count flow results/errors queries."""
  params = {}

  query = f"""
  SELECT COUNT(*)
  FROM {table_name} AS t
  """

  query += """
  WHERE t.ClientId = {client_id} AND t.FlowId = {flow_id}
  """

  params["client_id"] = spanner_clients.IntClientID(client_id)
  params["flow_id"] = IntFlowID(flow_id)

  if with_tag is not None:
    query += " AND t.Tag = {tag} "
    params["tag"] = with_tag

  if with_type is not None:
    query += " AND t.RdfType = {type}"
    params["type"] = with_type

  return query, params


_READ_FLOW_OBJECT_COLS = (
    "LongFlowId",
    "ParentFlowId",
    "ParentHuntId",
    "Creator",
    "Name",
    "State",
    "CreationTime",
    "UpdateTime",
    "Crash",
    "ProcessingWorker",
    "ProcessingStartTime",
    "ProcessingEndTime",
    "NextRequestToProcess",
    "Flow",
)


def _ParseReadFlowObjectRow(
    client_id: str,
    flow_id: str,
    row: Mapping[str, Any],
) -> flows_pb2.Flow:
  """Parses a row fetched with _READ_FLOW_OBJECT_COLS."""
  result = flows_pb2.Flow()
  result.ParseFromString(row["Flow"])

  creation_time = rdfvalue.RDFDatetime.FromDatetime(row["CreationTime"])
  update_time = rdfvalue.RDFDatetime.FromDatetime(row["UpdateTime"])

  # We treat column values as the source of truth for values, not the message
  # in the database itself. At least this is what the F1 implementation does.
  result.client_id = client_id
  result.flow_id = flow_id
  result.long_flow_id = row["LongFlowId"]

  if row["ParentFlowId"] is not None:
    result.parent_flow_id = db_utils.IntToFlowID(row["ParentFlowId"])
  if row["ParentHuntId"] is not None:
    result.parent_hunt_id = db_utils.IntToHuntID(row["ParentHuntId"])

  if row["Name"] is not None:
    result.flow_class_name = row["Name"]
  if row["Creator"] is not None:
    result.creator = row["Creator"]
  if row["State"] not in [None, flows_pb2.Flow.FlowState.UNSET]:
    result.flow_state = row["State"]
  if row["NextRequestToProcess"]:
    result.next_request_to_process = row["NextRequestToProcess"]

  result.create_time = int(creation_time)
  result.last_update_time = int(update_time)

  if row["Crash"] is not None:
    client_crash = jobs_pb2.ClientCrash()
    client_crash.ParseFromString(row["Crash"])
    result.client_crash_info.CopyFrom(client_crash)

  result.ClearField("processing_on")
  if row["ProcessingWorker"] is not None:
    result.processing_on = row["ProcessingWorker"]
  result.ClearField("processing_since")
  if row["ProcessingStartTime"] is not None:
    result.processing_since = int(
        rdfvalue.RDFDatetime.FromDatetime(row["ProcessingStartTime"])
    )
  result.ClearField("processing_deadline")
  if row["ProcessingEndTime"] is not None:
    result.processing_deadline = int(
        rdfvalue.RDFDatetime.FromDatetime(row["ProcessingEndTime"])
    )

  return result


class FlowsMixin:
  """A Spanner database mixin with implementation of flow methods."""

  db: spanner_utils.Database
  _write_rows_batch_size: int

  @property
  def _flow_processing_request_receiver(
      self,
  ) -> Optional[spanner_utils.RequestQueue]:
    return getattr(self, "__flow_processing_request_receiver", None)

  @_flow_processing_request_receiver.setter
  def _flow_processing_request_receiver(
      self, value: Optional[spanner_utils.RequestQueue]
  ) -> None:
    setattr(self, "__flow_processing_request_receiver", value)

  @property
  def _message_handler_receiver(self) -> Optional[spanner_utils.RequestQueue]:
    return getattr(self, "__message_handler_receiver", None)

  @_message_handler_receiver.setter
  def _message_handler_receiver(
      self, value: Optional[spanner_utils.RequestQueue]
  ) -> None:
    setattr(self, "__message_handler_receiver", value)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowObject(
      self,
      flow_obj: flows_pb2.Flow,
      allow_update: bool = True,
  ) -> None:
    """Writes a flow object to the database."""
    client_id = flow_obj.client_id
    flow_id = flow_obj.flow_id

    row = {
        "ClientId": spanner_clients.IntClientID(client_id),
        "FlowId": IntFlowID(flow_id),
        "LongFlowId": flow_obj.long_flow_id,
    }

    if flow_obj.parent_flow_id:
      row["ParentFlowId"] = IntFlowID(flow_obj.parent_flow_id)
    if flow_obj.parent_hunt_id:
      row["ParentHuntId"] = IntHuntID(flow_obj.parent_hunt_id)

    row["Creator"] = flow_obj.creator
    row["Name"] = flow_obj.flow_class_name
    row["State"] = int(flow_obj.flow_state)
    row["NextRequestToProcess"] = flow_obj.next_request_to_process

    row["CreationTime"] = spanner_lib.CommitTimestamp()
    row["UpdateTime"] = spanner_lib.CommitTimestamp()

    if flow_obj.HasField("client_crash_info"):
      row["Crash"] = flow_obj.client_crash_info

    if flow_obj.HasField("processing_on"):
      row["ProcessingWorker"] = flow_obj.processing_on
    if flow_obj.HasField("processing_since"):
      row["ProcessingStartTime"] = (
          rdfvalue.RDFDatetime()
          .FromMicrosecondsSinceEpoch(flow_obj.processing_since)
          .AsDatetime()
      )
    if flow_obj.HasField("processing_deadline"):
      row["ProcessingEndTime"] = (
          rdfvalue.RDFDatetime()
          .FromMicrosecondsSinceEpoch(flow_obj.processing_deadline)
          .AsDatetime()
      )

    row["Flow"] = flow_obj

    row["ReplyCount"] = spanner_lib.UInt64(flow_obj.num_replies_sent)
    row["NetworkBytesSent"] = spanner_lib.UInt64(flow_obj.network_bytes_sent)
    row["UserCpuTimeUsed"] = float(flow_obj.cpu_time_used.user_cpu_time)
    row["SystemCpuTimeUsed"] = float(flow_obj.cpu_time_used.system_cpu_time)

    try:
      if allow_update:
        self.db.InsertOrUpdate(
            table="Flows", row=row, txn_tag="WriteFlowObject_IOU"
        )
      else:
        self.db.Insert(table="Flows", row=row, txn_tag="WriteFlowObject_I")
    except spanner_errors.AlreadyExistsError as error:
      raise db.FlowExistsError(client_id, flow_id) from error
    except spanner_errors.RowNotFoundError as error:
      if "Parent row is missing: Clients" in str(error):
        raise db.UnknownClientError(client_id)
      else:
        raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadFlowObject(
      self,
      client_id: str,
      flow_id: str,
  ) -> flows_pb2.Flow:
    """Reads a flow object from the database."""
    int_client_id = spanner_clients.IntClientID(client_id)
    int_flow_id = IntFlowID(flow_id)

    try:
      row = self.db.Read(
          table="Flows",
          key=(int_client_id, int_flow_id),
          cols=_READ_FLOW_OBJECT_COLS,
      )
    except NotFound as error:
      raise db.UnknownFlowError(client_id, flow_id, cause=error)

    flow = _ParseReadFlowObjectRow(client_id, flow_id, row)
    return flow

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

    query = """
    SELECT f.ClientId, f.FlowId, f.LongFlowId,
           f.ParentFlowId, f.ParentHuntId,
           f.Creator, f.Name, f.State,
           f.CreationTime, f.UpdateTime,
           f.Crash, f.NextRequestToProcess,
           f.Flow
      FROM Flows AS f
    """
    params = {}

    conds = []

    if client_id is not None:
      params["client_id"] = spanner_clients.IntClientID(client_id)
      conds.append("f.ClientId = {client_id}")
    if parent_flow_id is not None:
      params["parent_flow_id"] = IntFlowID(parent_flow_id)
      conds.append("f.ParentFlowId = {parent_flow_id}")
    if min_create_time is not None:
      params["min_creation_time"] = min_create_time.AsDatetime()
      conds.append("f.CreationTime >= {min_creation_time}")
    if max_create_time is not None:
      params["max_creation_time"] = max_create_time.AsDatetime()
      conds.append("f.CreationTime <= {max_creation_time}")
    if not include_child_flows:
      conds.append("f.ParentFlowId IS NULL")
    if not_created_by is not None:
      params["not_created_by"] = spanner_lib.Array(str, not_created_by)
      conds.append("f.Creator NOT IN UNNEST({not_created_by})")

    if conds:
      query += f" WHERE {' AND '.join(conds)}"

    for row in self.db.ParamQuery(query, params, txn_tag="ReadAllFlowObjects"):
      int_client_id, int_flow_id, long_flow_id, *row = row
      int_parent_flow_id, int_parent_hunt_id, *row = row
      creator, name, state, *row = row
      creation_time, update_time, *row = row
      crash_bytes, next_request_to_process, flow_bytes = row

      flow = flows_pb2.Flow()
      flow.ParseFromString(flow_bytes)
      flow.client_id = db_utils.IntToClientID(int_client_id)
      flow.flow_id = db_utils.IntToFlowID(int_flow_id)
      flow.long_flow_id = long_flow_id
      flow.next_request_to_process = next_request_to_process

      if int_parent_flow_id is not None:
        flow.parent_flow_id = db_utils.IntToFlowID(int_parent_flow_id)
      if int_parent_hunt_id is not None:
        flow.parent_hunt_id = db_utils.IntToHuntID(int_parent_hunt_id)

      flow.creator = creator
      flow.flow_state = state
      flow.flow_class_name = name

      flow.create_time = rdfvalue.RDFDatetime.FromDatetime(
          creation_time
      ).AsMicrosecondsSinceEpoch()
      flow.last_update_time = rdfvalue.RDFDatetime.FromDatetime(
          update_time
      ).AsMicrosecondsSinceEpoch()

      if crash_bytes is not None:
        flow.client_crash_info.ParseFromString(crash_bytes)

      result.append(flow)

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateFlow(
      self,
      client_id: str,
      flow_id: str,
      flow_obj: Union[flows_pb2.Flow, _UNCHANGED_TYPE] = _UNCHANGED,
      flow_state: Union[
          flows_pb2.Flow.FlowState.ValueType, _UNCHANGED_TYPE
      ] = _UNCHANGED,
      client_crash_info: Union[
          jobs_pb2.ClientCrash, _UNCHANGED_TYPE
      ] = _UNCHANGED,
      processing_on: Optional[Union[str, _UNCHANGED_TYPE]] = _UNCHANGED,
      processing_since: Optional[
          Union[rdfvalue.RDFDatetime, _UNCHANGED_TYPE]
      ] = _UNCHANGED,
      processing_deadline: Optional[
          Union[rdfvalue.RDFDatetime, _UNCHANGED_TYPE]
      ] = _UNCHANGED,
  ) -> None:
    """Updates flow objects in the database."""

    row = {
        "ClientId": spanner_clients.IntClientID(client_id),
        "FlowId": IntFlowID(flow_id),
        "UpdateTime": spanner_lib.CommitTimestamp(),
    }

    if isinstance(flow_obj, flows_pb2.Flow):
      row["Flow"] = flow_obj
      row["State"] = int(flow_obj.flow_state)
      row["ReplyCount"] = spanner_lib.UInt64(flow_obj.num_replies_sent)
      row["NetworkBytesSent"] = spanner_lib.UInt64(flow_obj.network_bytes_sent)
      row["UserCpuTimeUsed"] = float(flow_obj.cpu_time_used.user_cpu_time)
      row["SystemCpuTimeUsed"] = float(flow_obj.cpu_time_used.system_cpu_time)
    if isinstance(flow_state, flows_pb2.Flow.FlowState.ValueType):
      row["State"] = int(flow_state)
    if isinstance(client_crash_info, jobs_pb2.ClientCrash):
      row["Crash"] = client_crash_info
    if (
        isinstance(processing_on, str) and processing_on is not db.UNCHANGED
    ) or processing_on is None:
      row["ProcessingWorker"] = processing_on
    if isinstance(processing_since, rdfvalue.RDFDatetime):
      row["ProcessingStartTime"] = processing_since.AsDatetime()
    if processing_since is None:
      row["ProcessingStartTime"] = None
    if isinstance(processing_deadline, rdfvalue.RDFDatetime):
      row["ProcessingEndTime"] = processing_deadline.AsDatetime()
    if processing_deadline is None:
      row["ProcessingEndTime"] = None

    try:
      self.db.Update(table="Flows", row=row, txn_tag="UpdateFlow")
    except spanner_errors.RowNotFoundError as error:
      raise db.UnknownFlowError(client_id, flow_id, cause=error)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowResults(self, results: Sequence[flows_pb2.FlowResult]) -> None:
    """Writes flow results for a given flow."""

    def Mutation(mut) -> None:
      for r in results:
        row = {
            "ClientId": spanner_clients.IntClientID(r.client_id),
            "FlowId": IntFlowID(r.flow_id),
            "HuntId": IntHuntID(r.hunt_id) if r.hunt_id else 0,
            "CreationTime": rdfvalue.RDFDatetime.Now().AsDatetime(),
            "Tag": r.tag,
            "RdfType": db_utils.TypeURLToRDFTypeName(r.payload.type_url),
            "Payload": r.payload,
        }

        mut.Insert("FlowResults", row)

    self.db.Mutate(Mutation, txn_tag="WriteFlowResults")

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowErrors(self, errors: Sequence[flows_pb2.FlowError]) -> None:
    """Writes flow errors for a given flow."""

    def Mutation(mut) -> None:
      for r in errors:
        row = {
            "ClientId": spanner_clients.IntClientID(r.client_id),
            "FlowId": IntFlowID(r.flow_id),
            "HuntId": IntHuntID(r.hunt_id) if r.hunt_id else 0,
            "CreationTime": rdfvalue.RDFDatetime.Now().AsDatetime(),
            "Payload": r.payload,
            "RdfType": db_utils.TypeURLToRDFTypeName(r.payload.type_url),
            "Tag": r.tag,
        }
        mut.Insert("FlowErrors", row)

    self.db.Mutate(Mutation, txn_tag="WriteFlowErrors")

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
    query, params = _BuildReadFlowResultsErrorsConditions(
        "FlowResults",
        client_id,
        flow_id,
        offset,
        count,
        with_tag,
        with_type,
        with_substring,
    )

    results = []
    for (
        payload_bytes,
        _,
        creation_time,
        tag,
        hunt_id,
    ) in self.db.ParamQuery(query, params, txn_tag="ReadFlowResults"):
      result = flows_pb2.FlowResult(
          client_id=client_id,
          flow_id=flow_id,
          timestamp=rdfvalue.RDFDatetime.FromDatetime(
              creation_time
          ).AsMicrosecondsSinceEpoch(),
      )
      result.payload.ParseFromString(payload_bytes)

      if hunt_id is not None:
        result.hunt_id = db_utils.IntToHuntID(hunt_id)

      if tag is not None:
        result.tag = tag

      results.append(result)

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
    query, params = _BuildReadFlowResultsErrorsConditions(
        "FlowErrors",
        client_id,
        flow_id,
        offset,
        count,
        with_tag,
        with_type,
        None,
    )

    errors = []
    for (
        payload_bytes,
        payload_type,
        creation_time,
        tag,
        hunt_id,
    ) in self.db.ParamQuery(query, params, txn_tag="ReadFlowErrors"):
      error = flows_pb2.FlowError(
          client_id=client_id,
          flow_id=flow_id,
          timestamp=rdfvalue.RDFDatetime.FromDatetime(
              creation_time
          ).AsMicrosecondsSinceEpoch(),
      )

      # TODO(b/309429206): for separation of concerns reasons,
      # ReadFlowResults/ReadFlowErrors shouldn't do the payload type validation,
      # they should be completely agnostic to what payloads get written/read
      # to/from the database. Keeping this logic here temporarily
      # to narrow the scope of the RDFProtoStruct->protos migration.
      if payload_type in rdfvalue.RDFValue.classes:
        error.payload.ParseFromString(payload_bytes)
      else:
        unrecognized = objects_pb2.SerializedValueOfUnrecognizedType(
            type_name=payload_type, value=payload_bytes
        )
        error.payload.Pack(unrecognized)

      if hunt_id is not None:
        error.hunt_id = db_utils.IntToHuntID(hunt_id)

      if tag is not None:
        error.tag = tag

      errors.append(error)

    return errors

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

    query, params = _BuildCountFlowResultsErrorsConditions(
        "FlowResults", client_id, flow_id, with_tag, with_type
    )
    (count,) = self.db.ParamQuerySingle(
        query, params, txn_tag="CountFlowResults"
    )
    return count

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

    query, params = _BuildCountFlowResultsErrorsConditions(
        "FlowErrors", client_id, flow_id, with_tag, with_type
    )
    (count,) = self.db.ParamQuerySingle(
        query, params, txn_tag="CountFlowErrors"
    )
    return count

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

    params = {
        "client_id": spanner_clients.IntClientID(client_id),
        "flow_id": IntFlowID(flow_id),
    }

    result = {}
    for type_name, count in self.db.ParamQuery(
        query, params, txn_tag="CountFlowResultsByType"
    ):
      result[type_name] = count

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountFlowErrorsByType(
      self, client_id: str, flow_id: str
  ) -> Mapping[str, int]:
    """Returns counts of flow errors grouped by error type."""

    query = """
    SELECT e.RdfType, COUNT(*)
    FROM FlowErrors AS e
    WHERE e.ClientId = {client_id} AND e.FlowId = {flow_id}
    GROUP BY RdfType
    """

    params = {
        "client_id": spanner_clients.IntClientID(client_id),
        "flow_id": IntFlowID(flow_id),
    }

    result = {}
    for type_name, count in self.db.ParamQuery(
        query, params, txn_tag="CountFlowErrorsByType"
    ):
      result[type_name] = count

    return result

  def _BuildFlowProcessingRequestWrites(
      self,
      mut: spanner_utils.Mutation,
      requests: Iterable[flows_pb2.FlowProcessingRequest],
  ) -> None:
    """Builds db writes for a list of FlowProcessingRequests."""

    for r in requests:
      key = (
          spanner_clients.IntClientID(r.client_id),
          IntFlowID(r.flow_id),
          spanner_lib.CommitTimestamp(),
      )

      ts = None
      if r.delivery_time:
        ts = rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
            r.delivery_time
        ).AsDatetimeUTC()

      mut.Send(
          queue="FlowProcessingRequestsQueue",
          key=key,
          value=r,
          column="Payload",
          deliver_time=ts,
      )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowProcessingRequests(
      self,
      requests: Sequence[flows_pb2.FlowProcessingRequest],
  ) -> None:
    """Writes a list of flow processing requests to the database."""

    def Mutation(mut) -> None:
      self._BuildFlowProcessingRequestWrites(mut, requests)

    self.db.BufferedMutate(Mutation, txn_tag="WriteFlowProcessingRequests")

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
    for payload, creation_time in self.db.ParamQuery(
        query, {}, txn_tag="ReadFlowProcessingRequests"
    ):
      req = flows_pb2.FlowProcessingRequest()
      req.ParseFromString(payload)
      req.creation_time = int(rdfvalue.RDFDatetime.FromDatetime(creation_time))
      results.append(req)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def AckFlowProcessingRequests(
      self, requests: Iterable[flows_pb2.FlowProcessingRequest]
  ) -> None:
    """Acknowledges and deletes flow processing requests."""

    def Mutation(mut) -> None:
      for r in requests:
        key = (
            spanner_clients.IntClientID(r.client_id),
            IntFlowID(r.flow_id),
            rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                r.creation_time
            ).AsDatetime(),
        )
        mut.Ack("FlowProcessingRequestsQueue", key)

    self.db.BufferedMutate(Mutation, txn_tag="AckFlowProcessingRequests")

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
    self.UnregisterFlowProcessingHandler()

    def Callback(expanded_key: Sequence[Any], payload: bytes):
      try:
        req = flows_pb2.FlowProcessingRequest()
        req.ParseFromString(payload)
        req.creation_time = int(
            rdfvalue.RDFDatetime.FromDatetime(expanded_key[2])
        )
        handler(req)
      except Exception as e:  # pylint: disable=broad-except
        logging.exception("Exception raised during Flow processing: %s", e)

    receiver = self.db.NewQueueReceiver(
        "FlowProcessingRequestsQueue",
        Callback,
        receiver_max_keepalive_seconds=3000,
        receiver_max_active_callbacks=50,
        receiver_max_messages_per_callback=1,
    )
    receiver.Receive()
    self._flow_processing_request_receiver = receiver

  def UnregisterFlowProcessingHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered flow processing handler."""
    del timeout  # Unused.
    if self._flow_processing_request_receiver is not None:
      # Pytype doesn't understand that the if-check above ensures that
      # _flow_processing_request_receiver is not None.
      self._flow_processing_request_receiver.Stop()  # pytype: disable=attribute-error
      self._flow_processing_request_receiver = None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowRequests(
      self,
      requests: Collection[flows_pb2.FlowRequest],
  ) -> None:
    """Writes a list of flow requests to the database."""

    flow_keys = [(r.client_id, r.flow_id) for r in requests]

    def Txn(txn) -> None:
      needs_processing = {}
      with txn.Mutate() as mut:
        for r in requests:
          if r.needs_processing:
            needs_processing.setdefault((r.client_id, r.flow_id), []).append(r)

          client_id_int = spanner_clients.IntClientID(r.client_id)
          flow_id_int = IntFlowID(r.flow_id)

          update_dict = {
              "ClientId": client_id_int,
              "FlowId": flow_id_int,
              "RequestId": r.request_id,
              "NeedsProcessing": r.needs_processing,
              "NextResponseId": r.next_response_id,
              "CallbackState": r.callback_state,
              "Payload": r,
              "CreationTime": spanner_lib.CommitTimestamp(),
          }
          if r.start_time:
            update_dict["StartTime"] = (
                rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                    r.start_time
                ).AsDatetime()
            )

          mut.InsertOrUpdate("FlowRequests", update_dict)

      if needs_processing:
        flow_processing_requests = []

        rows = spanner_lib.RowSet()
        # Note on linting: adding .keys() triggers a warning that
        # .keys() should be omitted. Omitting keys leads to a
        # mistaken warning that .items() was not called.
        for client_id, flow_id in needs_processing:  # pylint: disable=dict-iter-missing-items
          rows.Add(
              spanner_lib.Key(
                  spanner_clients.IntClientID(client_id), IntFlowID(flow_id)
              )
          )

        cols = (
            "ClientId",
            "FlowId",
            "NextRequestToProcess",
        )
        for row in txn.ReadSet(table="Flows", rows=rows, cols=cols):
          client_id = db_utils.IntToClientID(row["ClientId"])
          flow_id = db_utils.IntToFlowID(row["FlowId"])

          candidate_requests = needs_processing.get((client_id, flow_id), [])
          for r in candidate_requests:
            if row["NextRequestToProcess"] == r.request_id or r.start_time:
              req = flows_pb2.FlowProcessingRequest(
                  client_id=client_id, flow_id=flow_id
              )
              if r.start_time:
                req.delivery_time = r.start_time
              flow_processing_requests.append(req)

        if flow_processing_requests:
          with txn.BufferedMutate() as mut:
            self._BuildFlowProcessingRequestWrites(
                mut, flow_processing_requests
            )

    try:
      self.db.Transact(Txn, txn_tag="WriteFlowRequests")
    except spanner_errors.RowNotFoundError as error:
      if "Parent row is missing: Flows" in str(error):
        raise db.AtLeastOneUnknownFlowError(flow_keys, cause=error)
      else:
        raise

  def _ReadRequestsInfo(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
      txn,
  ) -> tuple[dict[_RequestKey, int], dict[_RequestKey, str], set[_RequestKey]]:
    """For given responses returns data about corresponding requests.

    Args:
      responses: an iterable with responses.
      txn: transaction to use.

    Returns:
      A tuple of 3 dictionaries: (
        responses_expected_by_request,
        callback_state_by_request,
        currently_available_requests).

      responses_expected_by_request: for requests that already received
      a Status response, maps each request id to the number of responses
      expected for it.

      callback_state_by_request: for incremental requests, maps each request
      id to the name of a flow callback state that has to be called on
      every incoming response.

      currently_available_requests: a set with all the request ids corresponding
      to given responses.
    """

    # Number of responses each affected request is waiting for (if available).
    responses_expected_by_request = {}

    # We also store all requests we have in the db so we can discard responses
    # for unknown requests right away.
    currently_available_requests = set()

    # Callback states by request.
    callback_state_by_request = {}

    req_rows = spanner_lib.RowSet()
    for r in responses:
      req_rows.Add(
          spanner_lib.Key(
              spanner_clients.IntClientID(r.client_id),
              IntFlowID(r.flow_id),
              r.request_id,
          )
      )

    for row in txn.ReadSet(
        table="FlowRequests",
        rows=req_rows,
        cols=[
            "ClientID",
            "FlowID",
            "RequestID",
            "CallbackState",
            "ExpectedResponseCount",
        ],
    ):

      request_key = _RequestKey(
          db_utils.IntToClientID(row["ClientID"]),
          db_utils.IntToFlowID(row["FlowID"]),
          row["RequestID"],
      )
      currently_available_requests.add(request_key)

      callback_state: str = row["CallbackState"]
      if callback_state:
        callback_state_by_request[request_key] = callback_state

      responses_expected: int = row["ExpectedResponseCount"]
      if responses_expected:
        responses_expected_by_request[request_key] = responses_expected

    return (
        responses_expected_by_request,
        callback_state_by_request,
        currently_available_requests,
    )

  def _BuildResponseWrites(
      self,
      responses: Collection[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
      txn,
  ) -> None:
    """Builds the writes to store given responses in the db.

    Args:
      responses: iterable with flow responses to write.
      txn: transaction to use for the writes.

    Raises:
      TypeError: if responses have objects other than FlowResponse, FlowStatus
          or FlowIterator.
    """

    with txn.Mutate() as mut:
      for r in responses:
        row = {
            "ClientId": spanner_clients.IntClientID(r.client_id),
            "FlowId": IntFlowID(r.flow_id),
            "RequestId": r.request_id,
            "ResponseId": r.response_id,
            "Response": None,
            "Status": None,
            "Iterator": None,
            "CreationTime": spanner_lib.CommitTimestamp(),
        }

        if isinstance(r, flows_pb2.FlowResponse):
          row["Response"] = r
        elif isinstance(r, flows_pb2.FlowStatus):
          row["Status"] = r
        elif isinstance(r, flows_pb2.FlowIterator):
          row["Iterator"] = r
        else:
          # This can't really happen due to DB validator type checking.
          raise TypeError(f"Got unexpected response type: {type(r)} {r}")

        mut.InsertOrUpdate("FlowResponses", row)

  def _BuildExpectedUpdates(
      self, updates: dict[_RequestKey, int], txn
  ) -> None:
    """Builds updates for requests with known number of expected responses.

    Args:
      updates: dict mapping requests to the number of expected responses.
      txn: transaction to use for the writes.
    """

    with txn.Mutate() as mut:
      for r_key, num_responses_expected in updates.items():
        row = {
            "ClientId": spanner_clients.IntClientID(r_key.client_id),
            "FlowId": IntFlowID(r_key.flow_id),
            "RequestId": r_key.request_id,
            "ExpectedResponseCount": num_responses_expected,
        }
        mut.Update("FlowRequests", row)

  def _WriteFlowResponsesAndExpectedUpdates(
      self,
      responses: Sequence[
          Union[
              flows_pb2.FlowResponse,
              flows_pb2.FlowStatus,
              flows_pb2.FlowIterator,
          ],
      ],
  ) -> tuple[dict[_RequestKey, int], dict[_RequestKey, str]]:
    """Writes a flow responses and updates flow requests expected counts.

    Args:
      responses: responses to write.

    Returns:
      A tuple of (expected_responses_by_request, callback_state_by_request).

      expected_responses_by_request: number of expected responses by
      request id. These numbers are collected from Status responses
      discovered in the `responses` sequence. This data is later
      passed to _BuildExpectedUpdates.

      callback_state_by_request: callback states by request. If incremental
      requests are discovered during processing, their callback states end
      up in this dictionary. This information is used later to make a
      decision whether a flow should be notified about new responses:
      incremental flows have to be notified even if Status responses were
      not received.
    """

    if not responses:
      return ({}, {})

    def Txn(
        txn: spanner_utils.Transaction,
    ) -> tuple[dict[_RequestKey, int], dict[_RequestKey, str]]:
      (
          responses_expected_by_request,
          callback_state_by_request,
          currently_available_requests,
      ) = self._ReadRequestsInfo(responses, txn)

      # For some requests we will need to update the number of expected
      # responses.
      needs_expected_update = {}

      for r in responses:
        req_key = _RequestKey(r.client_id, r.flow_id, r.request_id)

        # If the response is not a FlowStatus, we have nothing to do: it will be
        # simply written to the DB. If it's a FlowStatus, we have to update
        # the FlowRequest with the number of expected messages.
        if not isinstance(r, flows_pb2.FlowStatus):
          continue

        if req_key not in currently_available_requests:
          logging.info("Dropping status for unknown request %s", req_key)
          continue

        current = responses_expected_by_request.get(req_key)
        if current:
          logging.warning(
              "Got duplicate status message for request %s", req_key
          )

          # If there is already responses_expected information, we need to make
          # sure the current status doesn't disagree.
          if current != r.response_id:
            logging.error(
                "Got conflicting status information for request %s: %s",
                req_key,
                r,
            )
        else:
          needs_expected_update[req_key] = r.response_id

        responses_expected_by_request[req_key] = r.response_id

      responses_to_write = {}
      for r in responses:
        req_key = _RequestKey(r.client_id, r.flow_id, r.request_id)
        full_key = _ResponseKey(
            r.client_id, r.flow_id, r.request_id, r.response_id
        )

        if req_key not in currently_available_requests:
          continue

        if full_key in responses_to_write:
          # Don't write a response if it was already written as part of the
          # same batch.
          prev = responses_to_write[full_key]
          if r != prev:
            logging.warning(
                "WriteFlowResponses attempted to write two different "
                "entries with identical key %s. First is %s and "
                "second is %s.",
                full_key,
                prev,
                r,
            )
          continue

        responses_to_write[full_key] = r

      if responses_to_write or needs_expected_update:
        self._BuildResponseWrites(responses_to_write.values(), txn)
        if needs_expected_update:
          self._BuildExpectedUpdates(needs_expected_update, txn)

      return responses_expected_by_request, callback_state_by_request

    return self.db.Transact(
        Txn, txn_tag="WriteFlowResponsesAndExpectedUpdates"
    ).value

  def _GetFlowResponsesPerRequestCounts(
      self,
      request_keys: Iterable[_RequestKey],
      txn,
  ) -> dict[_RequestKey, int]:
    """Gets counts of already received responses for given requests.

    Args:
      request_keys: iterable with request keys.
      txn: transaction to use.

    Returns:
      A dictionary mapping request keys to the number of existing flow
      responses.
    """

    if not request_keys:
      return {}

    conditions = []
    params = {}
    for i, req_key in enumerate(request_keys):
      if i > 0:
        conditions.append("OR")

      conditions.append(f"""
         (fr.ClientId = {{client_id_{i}}} AND
         fr.FlowId = {{flow_id_{i}}} AND
         fr.RequestId = {{request_id_{i}}})
      """)

      params[f"client_id_{i}"] = db_utils.ClientIDToInt(req_key.client_id)
      params[f"flow_id_{i}"] = db_utils.FlowIDToInt(req_key.flow_id)
      params[f"request_id_{i}"] = req_key.request_id

    query = f"""
    SELECT fr.ClientId, fr.FlowId, fr.RequestId, COUNT(*) AS ResponseCount
    FROM FlowResponses as fr
    WHERE {" ".join(conditions)}
    GROUP BY fr.ClientID, fr.FlowID, fr.RequestID
    """

    result = {}
    for row in txn.ParamQuery(query, params):
      client_id_int, flow_id_int, request_id, count = row

      req_key = _RequestKey(
          db_utils.IntToClientID(client_id_int),
          db_utils.IntToFlowID(flow_id_int),
          request_id,
      )
      result[req_key] = count

    return result

  def _ReadFlowRequestsNotYetMarkedForProcessing(
      self,
      requests: set[_RequestKey],
      callback_states: dict[_RequestKey, str],
      txn,
  ) -> tuple[
      set[_RequestKey], set[tuple[_FlowKey, Optional[rdfvalue.RDFDatetime]]]
  ]:
    """Reads given requests and returns only ones not marked for processing.

    Args:
      requests: request keys for requests to be read.
      callback_states: dict containing incremental flow requests from the set.
        For each such request the request key will be mapped to the callback
        state of the flow.
      txn: transaction to use.

    Returns:
      A tuple of (requests_to_mark, flows_to_notify).

      requests_to_mark is a set of request keys for requests that have to be
      marked as needing processing.

      flows_to_notify is a set of tuples (flow_key, start_time) for flows that
      have to be notified of incoming responses. start_time in the tuple
      corresponds to the intended notification delivery time.
    """
    flow_rows = spanner_lib.RowSet()
    req_rows = spanner_lib.RowSet()

    unique_flow_keys = set()

    for req_key in set(requests) | set(callback_states):
      client_id_int = spanner_clients.IntClientID(req_key.client_id)
      flow_id_int = IntFlowID(req_key.flow_id)

      req_rows.AddPrefixRange(
          spanner_lib.Key(client_id_int, flow_id_int, req_key.request_id)
      )
      unique_flow_keys.add((client_id_int, flow_id_int))

    for client_id_int, flow_id_int in unique_flow_keys:
      flow_rows.AddPrefixRange(spanner_lib.Key(client_id_int, flow_id_int))

    next_request_to_process_by_flow = {}
    flow_cols = (
        "ClientId",
        "FlowId",
        "NextRequestToProcess",
    )
    for row in txn.ReadSet("Flows", flow_rows, flow_cols):
      client_id_int: int = row["ClientId"]
      flow_id_int: int = row["FlowId"]
      next_request_id: int = row["NextRequestToProcess"]
      next_request_to_process_by_flow[(client_id_int, flow_id_int)] = (
          next_request_id
      )

    requests_to_mark = set()
    requests_to_notify = set()
    req_cols = (
        "ClientId",
        "FlowId",
        "RequestId",
        "NeedsProcessing",
        "StartTime",
    )
    for row in txn.ReadSet("FlowRequests", req_rows, req_cols):
      client_id_int: int = row["ClientId"]
      flow_id_int: int = row["FlowId"]
      request_id: int = row["RequestId"]
      np: bool = row["NeedsProcessing"]
      start_time: Optional[rdfvalue.RDFDatetime] = None
      if row["StartTime"] is not None:
        start_time = rdfvalue.RDFDatetime.FromDatetime(row["StartTime"])

      if not np:
        client_id = db_utils.IntToClientID(client_id_int)
        flow_id = db_utils.IntToFlowID(flow_id_int)

        req_key = _RequestKey(client_id, flow_id, request_id)
        if req_key in requests:
          requests_to_mark.add(req_key)

        if (
            next_request_to_process_by_flow[(client_id_int, flow_id_int)]
            == request_id
        ):
          requests_to_notify.add((_FlowKey(client_id, flow_id), start_time))

    return requests_to_mark, requests_to_notify

  def _BuildNeedsProcessingUpdates(
      self, requests: set[_RequestKey], txn
  ) -> None:
    """Builds updates for requests that have their NeedsProcessing flag set.

    Args:
      requests: keys of requests to be updated.
      txn: transaction to use.
    """

    with txn.Mutate() as mut:
      for req_key in requests:
        row = {
            "ClientId": spanner_clients.IntClientID(req_key.client_id),
            "FlowId": IntFlowID(req_key.flow_id),
            "RequestId": req_key.request_id,
            "NeedsProcessing": True,
        }
        mut.Update("FlowRequests", row)

  def _UpdateNeedsProcessingAndWriteFlowProcessingRequests(
      self,
      requests_ready_for_processing: set[_RequestKey],
      callback_state_by_request: dict[_RequestKey, str],
      txn,
  ) -> None:
    """Updates requests needs-processing flags, writes processing requests.

    Args:
      requests_ready_for_processing: request keys for requests that have to be
        updated.
      callback_state_by_request: for incremental requests from the set - mapping
        from request ids to callback states that are incrementally processing
        incoming responses.
      txn: transaction to use.
    """

    if not requests_ready_for_processing and not callback_state_by_request:
      return

    (requests_to_mark, flows_to_notify) = (
        self._ReadFlowRequestsNotYetMarkedForProcessing(
            requests_ready_for_processing, callback_state_by_request, txn
        )
    )

    if requests_to_mark:
      self._BuildNeedsProcessingUpdates(requests_to_mark, txn)

    if flows_to_notify:
      flow_processing_requests = []
      for flow_key, start_time in flows_to_notify:
        fpr = flows_pb2.FlowProcessingRequest(
            client_id=flow_key.client_id,
            flow_id=flow_key.flow_id,
        )
        if start_time is not None:
          fpr.delivery_time = int(start_time)
        flow_processing_requests.append(fpr)

      with txn.BufferedMutate() as mut:
        self._BuildFlowProcessingRequestWrites(mut, flow_processing_requests)

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
    responses_expected_by_request = {}
    callback_state_by_request = {}
    for batch in collection.Batch(responses, self._write_rows_batch_size):
      res_exp_by_req_iter, callback_state_by_req_iter = (
          self._WriteFlowResponsesAndExpectedUpdates(batch)
      )

      responses_expected_by_request.update(res_exp_by_req_iter)
      callback_state_by_request.update(callback_state_by_req_iter)

    # If we didn't get any status messages, then there's nothing to process.
    if not responses_expected_by_request and not callback_state_by_request:
      return

    # Get actual per-request responses counts using a separate transaction.
    read_txn = self.db.Snapshot()
    counts = self._GetFlowResponsesPerRequestCounts(
        responses_expected_by_request, read_txn
    )

    requests_ready_for_processing = set()
    for req_key, responses_expected in responses_expected_by_request.items():
      if counts.get(req_key) == responses_expected:
        requests_ready_for_processing.add(req_key)

    # requests_to_notify is a subset of requests_ready_for_processing, so no
    # need to check if it's empty or not.
    if requests_ready_for_processing or callback_state_by_request:

      def Txn(txn) -> None:
        self._UpdateNeedsProcessingAndWriteFlowProcessingRequests(
            requests_ready_for_processing, callback_state_by_request, txn
        )

      self.db.Transact(Txn, txn_tag="WriteFlowResponses")

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> None:
    """Deletes all requests and responses for a given flow from the database."""
    int_client_id = spanner_clients.IntClientID(client_id)
    int_flow_id = IntFlowID(flow_id)
    self.db.DeleteWithPrefix(
        "FlowRequests",
        (int_client_id, int_flow_id),
        txn_tag="DeleteAllFlowRequestsAndResponses",
    )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAllFlowRequestsAndResponses(
      self,
      client_id: str,
      flow_id: str,
  ) -> Iterable[
      tuple[
          flows_pb2.FlowRequest,
          dict[
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

    txn = self.db.Snapshot()

    req_rows = spanner_lib.RowSet()
    req_rows.AddPrefixRange(
        spanner_lib.Key(
            spanner_clients.IntClientID(client_id), IntFlowID(flow_id)
        )
    )
    req_cols = (
        "Payload",
        "NeedsProcessing",
        "ExpectedResponseCount",
        "CallbackState",
        "NextResponseId",
        "CreationTime",
    )
    requests = []
    for row in txn.ReadSet(table="FlowRequests", rows=req_rows, cols=req_cols):
      request = flows_pb2.FlowRequest()
      request.ParseFromString(row["Payload"])
      request.needs_processing = row["NeedsProcessing"]
      if row["ExpectedResponseCount"] is not None:
        request.nr_responses_expected = row["ExpectedResponseCount"]
      request.callback_state = row["CallbackState"]
      request.next_response_id = row["NextResponseId"]
      request.timestamp = int(
          rdfvalue.RDFDatetime.FromDatetime(row["CreationTime"])
      )
      requests.append(request)

    resp_rows = spanner_lib.RowSet()
    resp_rows.AddPrefixRange(
        spanner_lib.Key(
            spanner_clients.IntClientID(client_id), IntFlowID(flow_id)
        )
    )
    resp_cols = (
        "Response",
        "Status",
        "Iterator",
        "CreationTime",
    )
    responses = {}
    for row in txn.ReadSet(
        table="FlowResponses", rows=resp_rows, cols=resp_cols
    ):
      if row["Status"] is not None:
        response = flows_pb2.FlowStatus()
        response.ParseFromString(row["Status"])
      elif row["Iterator"] is not None:
        response = flows_pb2.FlowIterator()
        response.ParseFromString(row["Iterator"])
      else:
        response = flows_pb2.FlowResponse()
        response.ParseFromString(row["Response"])
      response.timestamp = int(
          rdfvalue.RDFDatetime.FromDatetime(row["CreationTime"])
      )
      responses.setdefault(response.request_id, {})[
          response.response_id
      ] = response

    ret = []
    for req in sorted(requests, key=lambda r: r.request_id):
      ret.append((req, responses.get(req.request_id, {})))
    return ret

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteFlowRequests(
      self,
      requests: Sequence[flows_pb2.FlowRequest],
  ) -> None:
    """Deletes a list of flow requests from the database."""
    if not requests:
      return

    def Mutation(mut) -> None:
      for request in requests:
        key = [
            spanner_clients.IntClientID(request.client_id),
            IntFlowID(request.flow_id),
            request.request_id,
        ]
        mut.Delete(table="FlowRequests", key=key)

    try:
      self.db.Mutate(Mutation, txn_tag="DeleteFlowRequests")
    # TODO(b/196379916): Narrow the exception types (cl/450440276).
    except spanner_errors.BadUsageError:
      if len(requests) == 1:
        # If there is only one request and we still hit Spanner limits it means
        # that the requests has a lot of responses. It should be extremely rare
        # to end up in such situation, so we just leave the request in the
        # database. Eventually, these rows will be deleted automatically due to
        # our row retention policies [1] for this table.
        #
        # [1]: go/spanner-row-deletion-policies.
        SPANNER_DELETE_FLOW_REQUESTS_FAILURES.Increment()
        logging.error(
            "Transaction too big to delete flow request '%s'", requests[0]
        )
      else:
        # If there is more than one request, we attempt to divide the data into
        # smaller parts and delete these.
        #
        # Note that dividing in two does not mean that the number of deleted
        # rows will spread evenly as it might be the case that one request in
        # one part has significantly more responses than requests in the other
        # part. However, as a cheap and reasonable approximation, this should do
        # just fine.
        #
        # Notice that both this `DeleteFlowRequests` calls happen in separate
        # transactions. Since we are just deleting rows "obsolete" rows we do
        # not really care about atomicity. If one of them succeeds and the other
        # one fails, rows are going to be deleted eventually anyway (see the
        # comment for a single request case).
        self.DeleteFlowRequests(requests[: len(requests) // 2])
        self.DeleteFlowRequests(requests[len(requests) // 2 :])

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadFlowRequests(
      self,
      client_id: str,
      flow_id: str,
  ) -> dict[
      int,
      tuple[
          flows_pb2.FlowRequest,
          list[
              Union[
                  flows_pb2.FlowResponse,
                  flows_pb2.FlowStatus,
                  flows_pb2.FlowIterator,
              ],
          ],
      ],
  ]:
    """Reads all requests for a flow that can be processed by the worker."""

    txn = self.db.Snapshot()
    rows = spanner_lib.RowSet()
    rows.AddPrefixRange(
        spanner_lib.Key(
            spanner_clients.IntClientID(client_id), IntFlowID(flow_id)
        )
    )

    responses: dict[
        int,
        list[
            Union[
                flows_pb2.FlowResponse,
                flows_pb2.FlowStatus,
                flows_pb2.FlowIterator,
            ]
        ],
    ] = {}
    resp_cols = (
        "Response",
        "Status",
        "Iterator",
        "CreationTime",
    )
    for row in txn.ReadSet(table="FlowResponses", rows=rows, cols=resp_cols):
      if row["Status"]:
        response = flows_pb2.FlowStatus()
        response.ParseFromString(row["Status"])
      elif row["Iterator"]:
        response = flows_pb2.FlowIterator()
        response.ParseFromString(row["Iterator"])
      else:
        response = flows_pb2.FlowResponse()
        response.ParseFromString(row["Response"])
      response.timestamp = int(
          rdfvalue.RDFDatetime.FromDatetime(row["CreationTime"])
      )
      responses.setdefault(response.request_id, []).append(response)

    requests: dict[
        int,
        tuple[
            flows_pb2.FlowRequest,
            list[
                Union[
                    flows_pb2.FlowResponse,
                    flows_pb2.FlowStatus,
                    flows_pb2.FlowIterator,
                ],
            ],
        ],
    ] = {}
    req_cols = (
        "Payload",
        "NeedsProcessing",
        "ExpectedResponseCount",
        "NextResponseId",
        "CallbackState",
        "CreationTime",
    )
    for row in txn.ReadSet(table="FlowRequests", rows=rows, cols=req_cols):
      request = flows_pb2.FlowRequest()
      request.ParseFromString(row["Payload"])
      request.needs_processing = row["NeedsProcessing"]
      if row["ExpectedResponseCount"] is not None:
        request.nr_responses_expected = row["ExpectedResponseCount"]
      request.callback_state = row["CallbackState"]
      request.next_response_id = row["NextResponseId"]
      request.timestamp = int(
          rdfvalue.RDFDatetime.FromDatetime(row["CreationTime"])
      )
      requests[request.request_id] = (
          request,
          sorted(
              responses.get(request.request_id, []), key=lambda r: r.response_id
          ),
      )
    return requests

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateIncrementalFlowRequests(
      self,
      client_id: str,
      flow_id: str,
      next_response_id_updates: Mapping[int, int],
  ) -> None:
    """Updates next response ids of given requests."""

    int_client_id = spanner_clients.IntClientID(client_id)
    int_flow_id = IntFlowID(flow_id)

    with self.db.MutationPool() as mp:
      for request_id, response_id in next_response_id_updates.items():
        with mp.Apply() as mut:
          mut.Update(
              table="FlowRequests",
              row={
                  "ClientId": int_client_id,
                  "FlowId": int_flow_id,
                  "RequestId": request_id,
                  "NextResponseId": response_id,
              },
          )

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteFlowLogEntry(self, entry: flows_pb2.FlowLogEntry) -> None:
    """Writes a single flow log entry to the database."""
    row = {
        "ClientId": spanner_clients.IntClientID(entry.client_id),
        "FlowId": IntFlowID(entry.flow_id),
        "CreationTime": spanner_lib.CommitTimestamp(),
        "Message": entry.message,
    }

    if entry.hunt_id:
      row["HuntId"] = IntHuntID(entry.hunt_id)

    try:
      self.db.Insert(table="FlowLogEntries", row=row)
    except spanner_errors.RowNotFoundError as error:
      raise db.UnknownFlowError(entry.client_id, entry.flow_id) from error

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

    query = """
    SELECT l.HuntId,
           l.CreationTime,
           l.Message
      FROM FlowLogEntries AS l
     WHERE l.ClientId = {client_id}
       AND l.FlowId = {flow_id}
    """
    params = {
        "client_id": spanner_clients.IntClientID(client_id),
        "flow_id": IntFlowID(flow_id),
    }

    if with_substring is not None:
      query += " AND STRPOS(l.Message, {substring}) != 0"
      params["substring"] = with_substring

    query += """
     LIMIT {count}
    OFFSET {offset}
    """
    params["offset"] = offset
    params["count"] = count

    for row in self.db.ParamQuery(query, params):
      int_hunt_id, creation_time, message = row

      result = flows_pb2.FlowLogEntry()
      result.client_id = client_id
      result.flow_id = flow_id

      if int_hunt_id is not None:
        result.hunt_id = db_utils.IntToHuntID(int_hunt_id)

      result.timestamp = rdfvalue.RDFDatetime.FromDatetime(
          creation_time
      ).AsMicrosecondsSinceEpoch()
      result.message = message

      results.append(result)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountFlowLogEntries(self, client_id: str, flow_id: str) -> int:
    """Returns number of flow log entries of a given flow."""
    query = """
    SELECT COUNT(*)
      FROM FlowLogEntries AS l
     WHERE l.ClientId = {client_id}
       AND l.FlowId = {flow_id}
    """
    params = {
        "client_id": spanner_clients.IntClientID(client_id),
        "flow_id": IntFlowID(flow_id),
    }

    (count,) = self.db.ParamQuerySingle(query, params)
    return count

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
    # Mutations cannot be empty, so we exit early to avoid that if needed.
    if not logs:
      return

    def Mutation(mut) -> None:
      for response_id, log in logs.items():
        row = {
            "ClientId": db_utils.ClientIDToInt(client_id),
            "FlowId": db_utils.FlowIDToInt(flow_id),
            "RequestId": request_id,
            "ResponseId": response_id,
            "LogLevel": log.level,
            "LogTime": log.timestamp.ToDatetime(),
            "LogMessage": log.message,
            "CreationTime": spanner_lib.CommitTimestamp(),
        }
        mut.Insert(table="FlowRRGLogs", row=row)

    try:
      self.db.Mutate(Mutation)
    except spanner_errors.RowNotFoundError as error:
      raise db.UnknownFlowError(client_id, flow_id, cause=error) from error

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
    query = """
    SELECT
      l.LogLevel, l.LogTime, l.LogMessage
    FROM
      FlowRRGLogs AS l
    WHERE
      l.ClientId = {client_id} AND l.FlowId = {flow_id}
    ORDER BY
      l.RequestId, l.ResponseId
    LIMIT
      {count}
    OFFSET
      {offset}
    """
    params = {
        "client_id": db_utils.ClientIDToInt(client_id),
        "flow_id": db_utils.FlowIDToInt(flow_id),
        "offset": offset,
        "count": count,
    }

    results: list[rrg_pb2.Log] = []

    for row in self.db.ParamQuery(query, params, txn_tag="ReadFlowRRGLogs"):
      log_level, log_time, log_message = row

      log = rrg_pb2.Log()
      log.level = log_level
      log.timestamp.FromDatetime(log_time)
      log.message = log_message

      results.append(log)

    return results

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
    row = {
        "ClientId": spanner_clients.IntClientID(entry.client_id),
        "FlowId": IntFlowID(entry.flow_id),
        "OutputPluginId": IntOutputPluginID(entry.output_plugin_id),
        "CreationTime": spanner_lib.CommitTimestamp(),
        "Type": int(entry.log_entry_type),
        "Message": entry.message,
    }

    if entry.hunt_id:
      row["HuntId"] = IntHuntID(entry.hunt_id)

    try:
      self.db.Insert(table="FlowOutputPluginLogEntries", row=row)
    except spanner_errors.RowNotFoundError as error:
      raise db.UnknownFlowError(entry.client_id, entry.flow_id) from error

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

    query = """
    SELECT l.HuntId,
           l.CreationTime,
           l.Type, l.Message
      FROM FlowOutputPluginLogEntries AS l
     WHERE l.ClientId = {client_id}
       AND l.FlowId = {flow_id}
       AND l.OutputPluginId = {output_plugin_id}
    """
    params = {
        "client_id": spanner_clients.IntClientID(client_id),
        "flow_id": IntFlowID(flow_id),
        "output_plugin_id": IntOutputPluginID(output_plugin_id),
    }

    if with_type is not None:
      query += " AND l.Type = {type}"
      params["type"] = int(with_type)

    query += """
     LIMIT {count}
    OFFSET {offset}
    """
    params["offset"] = offset
    params["count"] = count

    for row in self.db.ParamQuery(query, params):
      int_hunt_id, creation_time, int_type, message = row

      result = flows_pb2.FlowOutputPluginLogEntry()
      result.client_id = client_id
      result.flow_id = flow_id
      result.output_plugin_id = output_plugin_id

      if int_hunt_id is not None:
        result.hunt_id = db_utils.IntToHuntID(int_hunt_id)

      result.timestamp = rdfvalue.RDFDatetime.FromDatetime(
          creation_time
      ).AsMicrosecondsSinceEpoch()
      result.log_entry_type = int_type
      result.message = message

      results.append(result)

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
    query = """
    SELECT COUNT(*)
      FROM FlowOutputPluginLogEntries AS l
     WHERE l.ClientId = {client_id}
       AND l.FlowId = {flow_id}
       AND l.OutputPluginId = {output_plugin_id}
    """
    params = {
        "client_id": spanner_clients.IntClientID(client_id),
        "flow_id": IntFlowID(flow_id),
        "output_plugin_id": IntOutputPluginID(output_plugin_id),
    }

    if with_type is not None:
      query += " AND l.Type = {type}"
      params["type"] = int(with_type)

    (count,) = self.db.ParamQuerySingle(query, params)
    return count

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteScheduledFlow(
      self,
      scheduled_flow: flows_pb2.ScheduledFlow,
  ) -> None:
    """Inserts or updates the ScheduledFlow in the database."""
    row = {
        "ClientID": spanner_clients.IntClientID(scheduled_flow.client_id),
        "Creator": scheduled_flow.creator,
        "ScheduledFlowId": IntFlowID(scheduled_flow.scheduled_flow_id),
        "FlowName": scheduled_flow.flow_name,
        "FlowArgs": scheduled_flow.flow_args,
        "RunnerArgs": scheduled_flow.runner_args,
        "CreationTime": rdfvalue.RDFDatetime(
            scheduled_flow.create_time
        ).AsDatetime(),
        "Error": scheduled_flow.error,
    }

    try:
      self.db.InsertOrUpdate(table="ScheduledFlows", row=row)
    except spanner_errors.RowNotFoundError as error:
      if "Parent row is missing: Clients" in str(error):
        raise db.UnknownClientError(scheduled_flow.client_id) from error
      elif "fk_creator_users_username" in str(error):
        raise db.UnknownGRRUserError(scheduled_flow.creator) from error
      else:
        raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteScheduledFlow(
      self,
      client_id: str,
      creator: str,
      scheduled_flow_id: str,
  ) -> None:
    """Deletes the ScheduledFlow from the database."""

    key = (
        spanner_clients.IntClientID(client_id),
        creator,
        IntFlowID(scheduled_flow_id),
    )

    def Transaction(txn) -> None:
      try:
        txn.Read(table="ScheduledFlows", cols=["ScheduledFlowId"], key=key)
      except spanner_errors.RowNotFoundError as e:
        raise db.UnknownScheduledFlowError(
            client_id=client_id,
            creator=creator,
            scheduled_flow_id=scheduled_flow_id,
        ) from e

      with txn.Mutate() as mut:
        mut.Delete(table="ScheduledFlows", key=key)

    self.db.Transact(Transaction)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ListScheduledFlows(
      self,
      client_id: str,
      creator: str,
  ) -> Sequence[flows_pb2.ScheduledFlow]:
    """Lists all ScheduledFlows for the client and creator."""
    rows = spanner_lib.RowSet()
    rows.AddPrefixRange(
        spanner_lib.Key(spanner_clients.IntClientID(client_id), creator)
    )

    cols = (
        "ClientId",
        "Creator",
        "ScheduledFlowId",
        "FlowName",
        "FlowArgs",
        "RunnerArgs",
        "CreationTime",
        "Error",
    )
    results = []

    for row in self.db.ReadSet("ScheduledFlows", rows, cols):
      sf = flows_pb2.ScheduledFlow()
      sf.client_id = db_utils.IntToClientID(row["ClientId"])
      sf.creator = row["Creator"]
      sf.scheduled_flow_id = db_utils.IntToFlowID(row["ScheduledFlowId"])
      sf.flow_name = row["FlowName"]
      sf.flow_args.ParseFromString(row["FlowArgs"])
      sf.runner_args.ParseFromString(row["RunnerArgs"])
      sf.create_time = int(
          rdfvalue.RDFDatetime.FromDatetime(row["CreationTime"])
      )
      sf.error = row["Error"]

      results.append(sf)

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    """Writes a list of message handler requests to the queue."""

    msgRequests = []
    for request in requests:
      msgRequests.append(request.SerializeToString())

    self.db.PublishMessageHandlerRequests(msgRequests)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadMessageHandlerRequests(
      self,
  ) -> Sequence[objects_pb2.MessageHandlerRequest]:
    """Reads all message handler requests from the queue."""

    results = []
    for result in self.db.ReadMessageHandlerRequests():
      req = objects_pb2.MessageHandlerRequest()
      req.ParseFromString(result["payload"])
      req.timestamp = rdfvalue.RDFDatetime.FromDatetime(
          result["publish_time"]
      ).AsMicrosecondsSinceEpoch()
      req.ack_id = result["ack_id"]
      results.append(req)

    return results

  def _BuildDeleteMessageHandlerRequestWrites(
      self,
      txn,
      requests: Iterable[objects_pb2.MessageHandlerRequest],
  ) -> None:
    """Deletes given requests within a given transaction."""
    req_rows = spanner_lib.RowSet()
    for r in requests:
      req_rows.AddPrefixRange(spanner_lib.Key(r.handler_name, r.request_id))

    to_delete = []
    req_cols = ("HandlerName", "RequestId", "CreationTime")
    for row in txn.ReadSet("MessageHandlerRequestsQueue", req_rows, req_cols):
      handler_name: str = row["HandlerName"]
      request_id: int = row["RequestId"]
      creation_time: datetime.datetime = row["CreationTime"]
      to_delete.append((handler_name, request_id, creation_time))

    with txn.BufferedMutate() as mut:
      for td_key in to_delete:
        mut.Ack("MessageHandlerRequestsQueue", td_key)

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteMessageHandlerRequests(
      self, requests: Iterable[objects_pb2.MessageHandlerRequest]
  ) -> None:
    """Deletes a list of message handler requests from the database."""

    ack_ids = []
    for request in requests:
      ack_ids.append(request.ack_id)

    self.db.AckMessageHandlerRequests(ack_ids)

  def _LeaseMessageHandlerRequest(
      self,
      req: objects_pb2.MessageHandlerRequest,
      lease_time: rdfvalue.Duration,
  ) -> bool:
    """Leases the given message handler request.

    Leasing of the message amounts to the following:
    1. The message gets deleted from the queue.
    2. It gets rescheduled in the future (at now + lease_time) with
      "leased_until" and "leased_by" attributes set.

    Args:
      req: MessageHandlerRequest to lease.
      lease_time: Lease duration.

    Returns:
      Copy of the original request object with "leased_until" and "leased_by"
      attributes set.
    """
    date_time_now = rdfvalue.RDFDatetime.Now()
    epoch_now = date_time_now.AsMicrosecondsSinceEpoch()
    delivery_time = date_time_now + lease_time

    leased = False
    if not req.leased_by or req.leased_until <= epoch_now:
      # If the message has not been leased yet or the lease has expired
      # then take and write back the clone back to the queue
      # and delete the original message 
      clone = objects_pb2.MessageHandlerRequest()
      clone.CopyFrom(req)
      clone.leased_until = delivery_time.AsMicrosecondsSinceEpoch()
      clone.leased_by = utils.ProcessIdString()
      clone.ack_id = ""
      self.WriteMessageHandlerRequests([clone])
      self.DeleteMessageHandlerRequests([req])
    elif req.leased_until > epoch_now:
      # if we have leased the message (leased_until set and in the future)
      # then we modify ack deadline to match the leased_until time
      leased = True
      ack_ids = []
      ack_ids.append(req.ack_id)
      self.db.LeaseMessageHandlerRequests(ack_ids, int((req.leased_until - epoch_now)/1000000))

    return leased

  def RegisterMessageHandler(
      self,
      handler: Callable[[Sequence[objects_pb2.MessageHandlerRequest]], None],
      lease_time: rdfvalue.Duration,
      limit: int = 1000,
  ) -> None:
    """Registers a message handler to receive batches of messages."""
    self.UnregisterMessageHandler()

    def Callback(payload: bytes, msg_id: str, ack_id: str, publish_time):
      try:
        req = objects_pb2.MessageHandlerRequest()
        req.ParseFromString(payload)
        req.ack_id = ack_id
        leased = self._LeaseMessageHandlerRequest(req, lease_time)
        if leased:
          logging.info("Leased message handler request: %s", req.request_id)
          handler([req])
      except Exception as e:  # pylint: disable=broad-except
        logging.exception(
            "Exception raised during MessageHandlerRequest processing: %s", e
        )

    receiver = self.db.NewRequestQueue(
        "MessageHandler",
        Callback,
        receiver_max_keepalive_seconds=_MESSAGE_HANDLER_MAX_KEEPALIVE_SECONDS,
        receiver_max_active_callbacks=_MESSAGE_HANDLER_MAX_ACTIVE_CALLBACKS,
        receiver_max_messages_per_callback=limit,
    )
    self._message_handler_receiver = receiver

  def UnregisterMessageHandler(
      self, timeout: Optional[rdfvalue.Duration] = None
  ) -> None:
    """Unregisters any registered message handler."""
    del timeout  # Unused.
    if self._message_handler_receiver:
      self._message_handler_receiver.Stop()  # pytype: disable=attribute-error  # always-use-return-annotations
      self._message_handler_receiver = None

  def _ReadHuntState(
      self, txn, hunt_id: str
  ) -> Optional[int]:
    try:
      row = txn.Read(table="Hunts", key=(IntHuntID(hunt_id),), cols=("State",))
      return row["State"]
    except spanner_errors.RowNotFoundError:
      return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def LeaseFlowForProcessing(
      self,
      client_id: str,
      flow_id: str,
      processing_time: rdfvalue.Duration,
  ) -> flows_pb2.Flow:
    """Marks a flow as being processed on this worker and returns it."""
    int_client_id = spanner_clients.IntClientID(client_id)
    int_flow_id = IntFlowID(flow_id)

    def Txn(txn) -> flows_pb2.Flow:
      try:
        row = txn.Read(
            table="Flows",
            key=(int_client_id, int_flow_id),
            cols=_READ_FLOW_OBJECT_COLS,
        )
      except spanner_errors.RowNotFoundError as error:
        raise db.UnknownFlowError(client_id, flow_id, cause=error)

      flow = _ParseReadFlowObjectRow(client_id, flow_id, row)
      now = rdfvalue.RDFDatetime.Now()
      if flow.processing_on and flow.processing_deadline > int(now):
        raise ValueError(
            "Flow {}/{} is already being processed on {} since {} "
            "with deadline {} (now: {})).".format(
                client_id,
                flow_id,
                flow.processing_on,
                rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                    flow.processing_since
                ),
                rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                    flow.processing_deadline
                ),
                now,
            )
        )

      if flow.parent_hunt_id is not None:
        hunt_state = self._ReadHuntState(txn, flow.parent_hunt_id)
        if (
            hunt_state is not None
            and not models_hunts.IsHuntSuitableForFlowProcessing(hunt_state)
        ):
          raise db.ParentHuntIsNotRunningError(
              client_id, flow_id, flow.parent_hunt_id, hunt_state
          )

      flow.processing_on = utils.ProcessIdString()
      flow.processing_deadline = int(now + processing_time)

      txn.Update(
          table="Flows",
          row={
              "ClientId": int_client_id,
              "FlowId": int_flow_id,
              "ProcessingWorker": flow.processing_on,
              "ProcessingEndTime": (
                  rdfvalue.RDFDatetime.FromMicrosecondsSinceEpoch(
                      flow.processing_deadline
                  ).AsDatetime()
              ),
              "ProcessingStartTime": spanner_lib.CommitTimestamp(),
          },
      )

      return flow

    result = self.db.Transact(Txn)

    leased_flow = result.value
    leased_flow.processing_since = int(
        rdfvalue.RDFDatetime.FromDatetime(result.commit_time)
    )
    return leased_flow

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReleaseProcessedFlow(self, flow_obj: flows_pb2.Flow) -> bool:
    """Releases a flow that the worker was processing to the database."""
    int_client_id = spanner_clients.IntClientID(flow_obj.client_id)
    int_flow_id = IntFlowID(flow_obj.flow_id)

    def Txn(txn) -> bool:
      try:
        row = txn.Read(
            table="FlowRequests",
            key=(int_client_id, int_flow_id, flow_obj.next_request_to_process),
            cols=("NeedsProcessing", "StartTime"),
        )
        if row["NeedsProcessing"]:
          start_time = row["StartTime"]
          if start_time is None:
            return False
          elif (
              rdfvalue.RDFDatetime.FromDatetime(start_time)
              < rdfvalue.RDFDatetime.Now()
          ):
            return False
      except spanner_errors.RowNotFoundError:
        pass
      txn.Update(
          table="Flows",
          row={
              "ClientId": int_client_id,
              "FlowId": int_flow_id,
              "Flow": flow_obj,
              "State": int(flow_obj.flow_state),
              "UserCpuTimeUsed": float(flow_obj.cpu_time_used.user_cpu_time),
              "SystemCpuTimeUsed": float(
                  flow_obj.cpu_time_used.system_cpu_time
              ),
              "NetworkBytesSent": spanner_lib.UInt64(
                  flow_obj.network_bytes_sent
              ),
              "ProcessingWorker": None,
              "ProcessingStartTime": None,
              "ProcessingEndTime": None,
              "NextRequesttoProcess": spanner_lib.UInt64(
                  flow_obj.next_request_to_process
              ),
              "UpdateTime": spanner_lib.CommitTimestamp(),
              "ReplyCount": flow_obj.num_replies_sent,
          },
      )

      return True

    return self.db.Transact(Txn).value


def IntFlowID(flow_id: str) -> int:
  """Converts a flow identifier to its integer representation.

  Args:
    flow_id: A flow identifier to convert.

  Returns:
    An integer representation of the given flow identifier.
  """
  return db_utils.FlowIDToInt(flow_id)


def IntHuntID(hunt_id: str) -> int:
  """Converts a hunt identifier to its integer representation.

  Args:
    hunt_id: A hunt identifier to convert.

  Returns:
    An integer representation of the given hunt identifier.
  """
  return db_utils.HuntIDToInt(hunt_id)


def IntOutputPluginID(output_plugin_id: str) -> int:
  """Converts an output plugin identifier to its integer representation.

  Args:
    output_plugin_id: An output plugin identifier to convert.

  Returns:
    An integer representation of the given output plugin identifier.
  """
  return db_utils.OutputPluginIDToInt(output_plugin_id)
