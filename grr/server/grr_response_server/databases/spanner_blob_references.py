#!/usr/bin/env python
"""A library with blob references methods of Spanner database implementation."""

from typing import Collection, Mapping, Optional

from grr_response_proto import objects_pb2
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils
from grr_response_server.rdfvalues import objects as rdf_objects


class BlobReferencesMixin:
  """A Spanner database mixin with implementation of blob references methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteHashBlobReferences(
      self,
      references_by_hash: Mapping[
          rdf_objects.SHA256HashID, Collection[objects_pb2.BlobReference]
      ],
  ) -> None:
    """Writes blob references for a given set of hashes."""


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadHashBlobReferences(
      self, hashes: Collection[rdf_objects.SHA256HashID]
  ) -> Mapping[
      rdf_objects.SHA256HashID, Optional[Collection[objects_pb2.BlobReference]]
  ]:
    """Reads blob references of a given set of hashes."""

    result = {}

    return result
