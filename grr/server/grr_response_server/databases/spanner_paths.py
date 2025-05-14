#!/usr/bin/env python
"""A module with path methods of the Spanner database implementation."""

from typing import Collection, Dict, Iterable, Optional, Sequence

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import iterator
from grr_response_proto import objects_pb2
from grr_response_server.databases import db as abstract_db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_clients
from grr_response_server.databases import spanner_utils
from grr_response_server.models import paths as models_paths


class PathsMixin:
  """A Spanner database mixin with implementation of path methods."""

  db: spanner_utils.Database

  # TODO(b/196379916): Implement path methods.

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WritePathInfos(
      self,
      client_id: str,
      path_infos: Iterable[objects_pb2.PathInfo],
  ) -> None:
    """Writes a collection of path records for a client."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Collection[Sequence[str]],
  ) -> dict[tuple[str, ...], Optional[objects_pb2.PathInfo]]:
    """Retrieves path info records for given paths."""

    return {}

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadPathInfo(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> objects_pb2.PathInfo:
    """Retrieves a path info record for a given path."""

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ListDescendantPathInfos(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components: Sequence[str],
      timestamp: Optional[rdfvalue.RDFDatetime] = None,
      max_depth: Optional[int] = None,
  ) -> Sequence[objects_pb2.PathInfo]:
    """Lists path info records that correspond to descendants of given path."""

    return []

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadPathInfosHistories(
      self,
      client_id: str,
      path_type: objects_pb2.PathInfo.PathType,
      components_list: Collection[Sequence[str]],
      cutoff: Optional[rdfvalue.RDFDatetime] = None,
  ) -> dict[tuple[str, ...], Sequence[objects_pb2.PathInfo]]:
    """Reads a collection of hash and stat entries for given paths."""


    results = {tuple(components): [] for components in components_list}

    params = {
        "client_id": spanner_clients.IntClientID(client_id),
        "type": int(path_type),
        "paths": list(map(EncodePathComponents, components_list)),
    }

    if cutoff is not None:
      stat_query += " AND s.CreationTime <= {cutoff}"
      hash_query += " AND h.CreationTime <= {cutoff}"
      params["cutoff"] = cutoff.AsDatetime()

    query = f"""
      WITH s AS ({stat_query}),
           h AS ({hash_query})
    SELECT s.Path, s.CreationTime, s.Stat,
           h.Path, h.CreationTime, h.Hash
      FROM s FULL JOIN h ON s.Path = h.Path
    """

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadLatestPathInfosWithHashBlobReferences(
      self,
      client_paths: Collection[abstract_db.ClientPath],
      max_timestamp: Optional[rdfvalue.RDFDatetime] = None,
  ) -> Dict[abstract_db.ClientPath, Optional[objects_pb2.PathInfo]]:
    """Returns path info with corresponding hash blob references."""
    # Early return in case of empty client paths to avoid issues with syntax er-
    # rors due to empty clause list.

    return {}
