#!/usr/bin/env python
"""A library with audit events methods of Spanner database implementation."""

from typing import Dict, List, Optional, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_proto import objects_pb2
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class EventsMixin:
  """A Spanner database mixin with implementation of audit events methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAPIAuditEntries(
      self,
      username: Optional[str] = None,
      router_method_names: Optional[List[str]] = None,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> List[objects_pb2.APIAuditEntry]:
    """Returns audit entries stored in the database."""
    query = """
    SELECT
      a.Username,
      a.CreationTime,
      a.HttpRequestPath,
      a.RouterMethodName,
      a.ResponseCode
    FROM ApiAuditEntry AS a
    """

    result = []

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def CountAPIAuditEntriesByUserAndDay(
      self,
      min_timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Dict[Tuple[str, rdfvalue.RDFDatetime], int]:
    """Returns audit entry counts grouped by user and calendar day."""

    result = {}

    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteAPIAuditEntry(self, entry: objects_pb2.APIAuditEntry):
    """Writes an audit entry to the database."""
