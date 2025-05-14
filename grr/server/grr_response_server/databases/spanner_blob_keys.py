#!/usr/bin/env python
"""Blob encryption key methods of Spanner database implementation."""

from typing import Collection, Dict, Optional

from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils
from grr_response_server.models import blobs as models_blobs


class BlobKeysMixin:
  """A Spanner mixin with implementation of blob encryption keys methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteBlobEncryptionKeys(
      self,
      key_names: Dict[models_blobs.BlobID, str],
  ) -> None:
    """Associates the specified blobs with the given encryption keys."""
    # A special case for empty list of blob identifiers to avoid issues with an
    # empty mutation.


  @db_utils.CallLogged
  @db_utils.CallAccounted
  def ReadBlobEncryptionKeys(
      self,
      blob_ids: Collection[models_blobs.BlobID],
  ) -> Dict[models_blobs.BlobID, Optional[str]]:
    """Retrieves encryption keys associated with blobs."""
    # A special case for empty list of blob identifiers to avoid syntax errors
    # in the query below.


    return {}
