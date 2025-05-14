"""A module with YARA methods of the Spanner database implementation."""

from google.cloud import spanner as spanner_lib
from grr_response_server.databases import db
from grr_response_server.databases import db_utils
from grr_response_server.databases import spanner_utils
from grr_response_server.models import blobs as models_blobs


class YaraMixin:
  """A Spanner database mixin with implementation of YARA methods."""

  db: spanner_utils.Database

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def WriteYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
      username: str,
  ) -> None:
    """Marks the specified blob id as a YARA signature."""
    row = {
        "BlobId": bytes(blob_id),
        "Creator": username,
        "CreationTime": spanner_lib.CommitTimestamp(),
    }

    try:
      self.db.InsertOrUpdate(
          table="YaraSignatureReferences",
          row=row,
          txn_tag="WriteYaraSignatureReference",
      )
    except NotFound as error:
      if "fk_yara_signature_reference_creator_username" in str(error):
        raise db.UnknownGRRUserError(username) from error
      else:
        raise

  @db_utils.CallLogged
  @db_utils.CallAccounted
  def VerifyYaraSignatureReference(
      self,
      blob_id: models_blobs.BlobID,
  ) -> bool:
    """Verifies whether the specified blob is a YARA signature."""
    key = (bytes(blob_id),)

    try:
      self.db.Read(table="YaraSignatureReferences", key=key, cols=())
    except NotFound:
      return False

    return True