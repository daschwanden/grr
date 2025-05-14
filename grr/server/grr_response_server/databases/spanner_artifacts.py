#!/usr/bin/env python
"""A module with artifacts methods of the Spanner backend."""

from typing import Optional, Sequence

from grr_response_proto import artifact_pb2
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils


class ArtifactsMixin:
  """A Spanner database mixin with implementation of artifacts."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteArtifact(self, artifact: artifact_pb2.Artifact) -> None:
    """Writes new artifact to the database.

    Args:
      artifact: Artifact to be stored.

    Raises:
      DuplicatedArtifactError: when the artifact already exists.
    """
 

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadArtifact(self, name: str) -> Optional[artifact_pb2.Artifact]:
    """Looks up an artifact with given name from the database.

    Args:
      name: Name of the artifact to be read.

    Returns:
      The artifact object read from the database.

    Raises:
      UnknownArtifactError: when the artifact does not exist.
    """

    return None

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadAllArtifacts(self) -> Sequence[artifact_pb2.Artifact]:
    """Lists all artifacts that are stored in the database."""
    result = []


    return result

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def DeleteArtifact(self, name: str) -> None:
    """Deletes an artifact with given name from the database.

    Args:
      name: Name of the artifact to be deleted.

    Raises:
      UnknownArtifactError when the artifact does not exist.
    """

