#!/usr/bin/env python
"""A module with client methods of the Spanner database implementation."""

import datetime
import logging
import re
from typing import Collection, Iterator, Mapping, Optional, Sequence, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import iterator
from grr_response_proto import jobs_pb2
from grr_response_proto import objects_pb2
# Aliasing the import since the name db clashes with the db annotation.
from grr_response_server.databases import db as db_lib
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils
from grr_response_server.models import clients as models_clients
from grr_response_proto.rrg import startup_pb2 as rrg_startup_pb2


class ClientsMixin:
  """A Spanner database mixin with implementation of client methods."""

  db: spanner_utils.Database

  # TODO(b/196379916): Implement client methods.

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiWriteClientMetadata(
      self,
      client_ids: Collection[str],
      first_seen: Optional[rdfvalue.RDFDatetime] = None,
      last_ping: Optional[rdfvalue.RDFDatetime] = None,
      last_foreman: Optional[rdfvalue.RDFDatetime] = None,
      fleetspeak_validation_info: Optional[Mapping[str, str]] = None,
  ) -> None:
    """Writes metadata about the clients."""
    # Early return to avoid generating empty mutation.


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiReadClientMetadata(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, objects_pb2.ClientMetadata]:
    """Reads ClientMetadata records for a list of clients."""
    result = {}

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiAddClientLabels(
      self,
      client_ids: Collection[str],
      owner: str,
      labels: Collection[str],
  ) -> None:
    """Attaches user labels to the specified clients."""
    # Early return to avoid generating empty mutation.


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiReadClientLabels(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, Collection[objects_pb2.ClientLabel]]:
    """Reads the user labels for a list of clients."""
    result = {client_id: [] for client_id in client_ids}

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def RemoveClientLabels(
      self,
      client_id: str,
      owner: str,
      labels: Collection[str],
  ) -> None:
    """Removes a list of user labels from a given client."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAllClientLabels(self) -> Collection[str]:
    """Lists all client labels known to the system."""
    result = []


    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteClientSnapshot(self, snapshot: objects_pb2.ClientSnapshot) -> None:
    """Writes new client snapshot."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiReadClientSnapshot(
      self,
      client_ids: Collection[str],
  ) -> Mapping[str, Optional[objects_pb2.ClientSnapshot]]:
    """Reads the latest client snapshots for a list of clients."""
    # Unfortunately, Spanner has troubles with handling `UNNEST` expressions if
    # the given array is empty, so we just handle such case separately.

    return {}

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientSnapshotHistory(
      self,
      client_id: str,
      timerange: Optional[
          Tuple[Optional[rdfvalue.RDFDatetime], Optional[rdfvalue.RDFDatetime]]
      ] = None,
  ) -> Sequence[objects_pb2.ClientSnapshot]:
    """Reads the full history for a particular client."""
    result = []

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteClientStartupInfo(
      self,
      client_id: str,
      startup: jobs_pb2.StartupInfo,
  ) -> None:
    """Writes a new client startup record."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteClientRRGStartup(
      self,
      client_id: str,
      startup: rrg_startup_pb2.Startup,
  ) -> None:
    """Writes a new RRG startup entry to the database."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientRRGStartup(
      self,
      client_id: str,
  ) -> Optional[rrg_startup_pb2.Startup]:
    """Reads the latest RRG startup entry for the given client."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientStartupInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.StartupInfo]:
    """Reads the latest client startup record for a single client."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteClientCrashInfo(
      self,
      client_id: str,
      crash: jobs_pb2.ClientCrash,
  ) -> None:
    """Writes a new client crash record."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientCrashInfo(
      self,
      client_id: str,
  ) -> Optional[jobs_pb2.ClientCrash]:
    """Reads the latest client crash record for a single client."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientCrashInfoHistory(
      self,
      client_id: str,
  ) -> Sequence[jobs_pb2.ClientCrash]:
    """Reads the full crash history for a particular client."""
    result = []

    query = """
    SELECT cr.CreationTime, cr.Crash
      FROM ClientCrashes AS cr
     WHERE cr.ClientId = {client_id}
     ORDER BY cr.CreationTime DESC
    """
    return None

  # TODO(b/196379916): Investigate whether we need to batch this call or not.
  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiReadClientFullInfo(
      self,
      client_ids: Collection[str],
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, objects_pb2.ClientFullInfo]:
    """Reads full client information for a list of clients."""
    # Spanner is having issues with `UNNEST` on empty arrays so we exit early in
    # such cases.

    result = {}

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadClientLastPings(
      self,
      min_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      max_last_ping: Optional[rdfvalue.RDFDatetime] = None,
      batch_size: int = 0,
  ) -> Iterator[Mapping[str, Optional[rdfvalue.RDFDatetime]]]:
    """Yields dicts of last-ping timestamps for clients in the DB."""



  def _ReadClientLastPingsBatch(
      self,
      count: int,
      last_client_id: str,
      min_last_ping_time: Optional[rdfvalue.RDFDatetime],
      max_last_ping_time: Optional[rdfvalue.RDFDatetime],
  ) -> Mapping[str, Optional[rdfvalue.RDFDatetime]]:
    """Reads a single batch of last client last ping times.

    Args:
      count: The number of entries to read in the batch.
      last_client_id: The identifier of the last client of the previous batch.
      min_last_ping_time: An (optional) lower bound on the last ping time value.
      max_last_ping_time: An (optional) upper bound on the last ping time value.

    Returns:
      A mapping from client identifiers to client last ping times.
    """
    result = {}

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteClient(self, client_id: str) -> None:
    """Deletes a client with all associated metadata."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def MultiAddClientKeywords(
      self,
      client_ids: Collection[str],
      keywords: Collection[str],
  ) -> None:
    """Associates the provided keywords with the specified clients."""
    # Early return to avoid generating empty mutation.


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ListClientsForKeywords(
      self,
      keywords: Collection[str],
      start_time: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Mapping[str, Collection[str]]:
    """Lists the clients associated with keywords."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def RemoveClientKeyword(self, client_id: str, keyword: str) -> None:
    """Removes the association of a particular client to a keyword."""



def IntClientID(client_id: str) -> int:
  """Converts a client identifier to its integer representation.

  This function wraps the value in PySpanner's `UInt64` wrapper. It is needed
  because by default PySpanner assumes that integers are `Int64` and this can
  cause conversion errors for large values.

  Args:
    client_id: A client identifier to convert.

  Returns:
    An integer representation of the given client identifier.
  """
  return db_utils.ClientIDToInt(client_id)


_EPOCH = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)

# TODO(b/196379916): The F1 implementation uses a single constant for all
# queries deleting a lot of data. We should probably follow this pattern here,
# this constant should be moved to a more appropriate module. Also, it might
# be worthwhile to use Spanner's partitioned DML feature [1].
#
# pylint: disable=line-too-long
# [1]: https://g3doc.corp.google.com/spanner/g3doc/userguide/sqlv1/data-manipulation-language.md#a-note-about-locking
# pylint: enable=line-too-long
_DELETE_BATCH_SIZE = 5_000
