#!/usr/bin/env python
"""A module with signed binaries methods of the Spanner backend."""

from typing import Sequence, Tuple

from grr_response_core.lib import rdfvalue
from grr_response_core.lib.util import iterator
from grr_response_proto import objects_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class SignedBinariesMixin:
  """A Spanner database mixin with implementation of signed binaries."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
      references: objects_pb2.BlobReferences,
  ) -> None:
    """Writes blob references for a signed binary to the DB.

    Args:
      binary_id: Signed binary id for the binary.
      references: Blob references for the given binary.
    """


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadSignedBinaryReferences(
      self, binary_id: objects_pb2.SignedBinaryID
  ) -> Tuple[objects_pb2.BlobReferences, rdfvalue.RDFDatetime]:
    """Reads blob references for the signed binary with the given id.

    Args:
      binary_id: Signed binary id for the binary.

    Returns:
      A tuple of the signed binary's rdf_objects.BlobReferences and an
      RDFDatetime representing the time when the references were written to the
      DB.
    """

    return None, None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadIDsForAllSignedBinaries(self) -> Sequence[objects_pb2.SignedBinaryID]:
    """Returns ids for all signed binaries in the DB."""
    results = []

    return results

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteSignedBinaryReferences(
      self,
      binary_id: objects_pb2.SignedBinaryID,
  ) -> None:
    """Deletes blob references for the given signed binary from the DB.

    Does nothing if no entry with the given id exists in the DB.

    Args:
      binary_id: An id of the signed binary to delete.
    """

