"""A BlobStore backed by Google Cloud Storage."""

import logging
import os
from typing import Dict, Iterable, Optional

from google.auth.credentials import AnonymousCredentials
from google.cloud import exceptions
from google.cloud import storage
from google.cloud.storage.retry import DEFAULT_RETRY
from grr_response_core import config
from grr_response_server import blob_store
from grr_response_server.rdfvalues import objects as rdf_objects


class GCSBlobStore(blob_store.BlobStore):
  """A BlobStore implementation backed by Google Cloud Storage."""

  def __init__(self):
    """Instantiates a new GCSBlobStore."""
    project = config.CONFIG["Blobstore.gcs.project"]
    bucket_name = config.CONFIG["Blobstore.gcs.bucket"]
    blob_prefix = config.CONFIG["Blobstore.gcs.blob_prefix"]

    # TODO: move to config
    if os.getenv("STORAGE_EMULATOR_HOST"):
      self._client = storage.Client(
          project=project, credentials=AnonymousCredentials()
      )
    else:
      self._client = storage.Client(project=project)

    self._bucket = self._client.bucket(bucket_name)
    self._blob_prefix = blob_prefix

  def _GetFilename(self, blob_id: rdf_objects.BlobID) -> str:
    hex_blob_id = blob_id.AsHexString()
    return f"{self._blob_prefix}/{hex_blob_id}"

  def WriteBlobs(
      self, blob_id_data_map: Dict[rdf_objects.BlobID, bytes]
  ) -> None:
    """Creates or overwrites blobs."""
    for blob_id, blob in blob_id_data_map.items():
      filename = self._GetFilename(blob_id)

      logging.info("Writing blob '%s' as '%s'", blob_id, filename)
      try:
        b = self._bucket.blob(filename)
        try:
          if b.exists():
            continue
        except Exception:
          pass
        b.upload_from_string(
            data=blob,
            content_type="application/octet-stream",
            retry=DEFAULT_RETRY,
        )
      except Exception as e:
        logging.error("Unable to write blob %s to datastore, %s", blob_id, e)

  def ReadBlob(self, blob_id: rdf_objects.BlobID) -> Optional[bytes]:
    """Reads the blob contexts, identified by the given BlobID."""
    filename = self._GetFilename(blob_id)
    try:
      b = self._bucket.blob(filename)
      return b.download_as_bytes(retry=DEFAULT_RETRY)
    except exceptions.NotFound:
      return None
    except Exception as e:
      logging.error("Unable to read blob %s, %s", blob_id, e)
      raise

  def ReadBlobs(
      self, blob_ids: Iterable[rdf_objects.BlobID]
  ) -> Dict[rdf_objects.BlobID, Optional[bytes]]:
    """Reads all blobs, specified by blob_ids, returning their contents."""
    return {blob_id: self.ReadBlob(blob_id) for blob_id in blob_ids}

  def CheckBlobExists(self, blob_id: rdf_objects.BlobID) -> bool:
    """Checks if a blob with a given BlobID exists."""
    filename = self._GetFilename(blob_id)
    try:
      b = self._bucket.blob(filename)
      return b.exists(retry=DEFAULT_RETRY)
    except Exception as e:
      logging.error("Unable to check for blob %s, %s", blob_id, e)
      raise

  def CheckBlobsExist(
      self, blob_ids: Iterable[rdf_objects.BlobID]
  ) -> Dict[rdf_objects.BlobID, bool]:
    """Checks if blobs for the given identifiers already exist."""
    return {blob_id: self.CheckBlobExists(blob_id) for blob_id in blob_ids}
