#!/usr/bin/env python
"""A module with hunt methods of the Spanner database implementation."""

from typing import AbstractSet, Callable, Collection, Iterable, List, Mapping, Optional, Sequence

from google.api_core.exceptions import AlreadyExists

from google.cloud import spanner as spanner_lib

from google.protobuf import any_pb2
from grr_response_core.lib import rdfvalue
from grr_response_core.lib.rdfvalues import client as rdf_client
from grr_response_proto import flows_pb2
from grr_response_proto import hunts_pb2
from grr_response_proto import jobs_pb2
from grr_response_proto import output_plugin_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_flows
from grr_response_server.databases import spanner_utils
from grr_response_server.models import hunts as models_hunts


class HuntsMixin:
  """A Spanner database mixin with implementation of flow methods."""

  db: spanner_utils.Database
  _write_rows_batch_size: int

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteHuntObject(self, hunt_obj: hunts_pb2.Hunt):
    """Writes a hunt object to the database."""
    row = {
        "HuntId": hunt_obj.hunt_id,
        "CreationTime": spanner_lib.COMMIT_TIMESTAMP,
        "LastUpdateTime": spanner_lib.COMMIT_TIMESTAMP,
        "Creator": hunt_obj.creator,
        "DurationMicros": hunt_obj.duration * 10**6,
        "Description": hunt_obj.description,
        "ClientRate": float(hunt_obj.client_rate),
        "ClientLimit": hunt_obj.client_limit,
        "State": int(hunt_obj.hunt_state),
        "StateReason": int(hunt_obj.hunt_state_reason),
        "StateComment": hunt_obj.hunt_state_comment,
        "InitStartTime": None,
        "LastStartTime": None,
        "ClientCountAtStartTime": hunt_obj.num_clients_at_start_time,
        "Hunt": hunt_obj,
    }

    try:
      self.db.Insert(table="Hunts", row=row, txn_tag="WriteHuntObject")
    except AlreadyExists as error:
      raise abstract_db.DuplicatedHuntError(
          hunt_id=hunt_obj.hunt_id, cause=error
      )


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateHuntObject(
      self,
      hunt_id: str,
      duration: Optional[rdfvalue.Duration] = None,
      client_rate: Optional[int] = None,
      client_limit: Optional[int] = None,
      hunt_state: Optional[hunts_pb2.Hunt.HuntState.ValueType] = None,
      hunt_state_reason: Optional[
          hunts_pb2.Hunt.HuntStateReason.ValueType
      ] = None,
      hunt_state_comment: Optional[str] = None,
      start_time: Optional[rdfvalue.RDFDatetime] = None,
      num_clients_at_start_time: Optional[int] = None,
  ):
    """Updates the hunt object."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteHuntObject(self, hunt_id: str) -> None:
    """Deletes a hunt object with a given id."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntObject(self, hunt_id: str) -> hunts_pb2.Hunt:
    """Reads a hunt object from the database."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntObjects(
      self,
      offset: int,
      count: int,
      with_creator: Optional[str] = None,
      created_after: Optional[rdfvalue.RDFDatetime] = None,
      with_description_match: Optional[str] = None,
      created_by: Optional[AbstractSet[str]] = None,
      not_created_by: Optional[AbstractSet[str]] = None,
      with_states: Optional[
          Collection[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None,
  ) -> List[hunts_pb2.Hunt]:
    """Reads hunt objects from the database."""

    result = []

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ListHuntObjects(
      self,
      offset: int,
      count: int,
      with_creator: Optional[str] = None,
      created_after: Optional[rdfvalue.RDFDatetime] = None,
      with_description_match: Optional[str] = None,
      created_by: Optional[Iterable[str]] = None,
      not_created_by: Optional[Iterable[str]] = None,
      with_states: Optional[
          Iterable[hunts_pb2.Hunt.HuntState.ValueType]
      ] = None,
  ) -> Iterable[hunts_pb2.HuntMetadata]:
    """Reads metadata for hunt objects from the database."""

    result = []

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntResults(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
      with_substring: Optional[str] = None,
      with_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Iterable[flows_pb2.FlowResult]:
    """Reads hunt results of a given hunt using given query options."""

    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntResults(
      self,
      hunt_id: str,
      with_tag: Optional[str] = None,
      with_type: Optional[str] = None,
  ) -> int:
    """Counts hunt results of a given hunt using given query options."""

    return 0

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntResultsByType(self, hunt_id: str) -> Mapping[str, int]:
    """Returns counts of items in hunt results grouped by type."""

    result = {}

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntLogEntries(
      self,
      hunt_id: str,
      offset: int,
      count: int,
      with_substring: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowLogEntry]:
    """Reads hunt log entries of a given hunt using given query options."""

    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntLogEntries(self, hunt_id: str) -> int:
    """Returns number of hunt log entries of a given hunt."""

    return 0

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      offset: int,
      count: int,
      with_type: Optional[str] = None,
  ) -> Sequence[flows_pb2.FlowOutputPluginLogEntry]:
    """Reads hunt output plugin log entries."""

    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntOutputPluginLogEntries(
      self,
      hunt_id: str,
      output_plugin_id: str,
      with_type: Optional[str] = None,
  ) -> int:
    """Returns number of hunt output plugin log entries of a given hunt."""

    return 0

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntOutputPluginsStates(
      self, hunt_id: str
  ) -> List[output_plugin_pb2.OutputPluginState]:
    """Reads all hunt output plugins states of a given hunt."""

    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteHuntOutputPluginsStates(
      self,
      hunt_id: str,
      states: Collection[output_plugin_pb2.OutputPluginState],
  ) -> None:
    """Writes hunt output plugin states for a given hunt."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def UpdateHuntOutputPluginState(
      self,
      hunt_id: str,
      state_index: int,
      update_fn: Callable[[jobs_pb2.AttributedDict], jobs_pb2.AttributedDict],
  ) -> None:
    """Updates hunt output plugin state for a given output plugin."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntFlows(  # pytype: disable=annotation-type-mismatch
      self,
      hunt_id: str,
      offset: int,
      count: int,
      filter_condition: abstract_db.HuntFlowsCondition = abstract_db.HuntFlowsCondition.UNSET,
  ) -> Sequence[flows_pb2.Flow]:
    """Reads hunt flows matching given conditions."""

    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntFlowErrors(
      self,
      hunt_id: str,
      offset: int,
      count: int,
  ) -> Mapping[str, abstract_db.FlowErrorInfo]:
    """Returns errors for flows of the given hunt."""
    results = {}

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountHuntFlows(  # pytype: disable=annotation-type-mismatch
      self,
      hunt_id: str,
      filter_condition: Optional[
          abstract_db.HuntFlowsCondition
      ] = abstract_db.HuntFlowsCondition.UNSET,
  ) -> int:
    """Counts hunt flows matching given conditions."""

    return 0

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntFlowsStatesAndTimestamps(
      self,
      hunt_id: str,
  ) -> Sequence[abstract_db.FlowStateAndTimestamps]:
    """Reads hunt flows states and timestamps."""

    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntsCounters(
      self,
      hunt_ids: Collection[str],
  ) -> Mapping[str, abstract_db.HuntCounters]:
    """Reads hunt counters for several of hunt ids."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHuntClientResourcesStats(
      self,
      hunt_id: str,
  ) -> jobs_pb2.ClientResourcesStats:
    """Read hunt client resources stats."""

    return None
