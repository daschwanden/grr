"""Spanner-related helpers and other utilities."""

from collections.abc import Callable, Iterable, Mapping, Sequence
import datetime
import decimal
import logging
import re
from typing import Any, Optional, Tuple, TypeVar

from google.cloud.spanner_v1 import database as spanner_lib
from google.cloud.spanner_v1.transaction import Transaction as _Transaction
from google.cloud.spanner_v1.batch import _BatchBase as _Mutation

from google.cloud.spanner import KeyRange, KeySet
from google.cloud.spanner_v1 import param_types

from grr_response_core.lib.util import collection


Row = Tuple[Any, ...]
Cursor = Iterable[Row]

_T = TypeVar("_T")

# Aliases so that users of this module do not have to depend on PySpanner
# internals directly (e.g. for type annotations).
Mutation = _Mutation
Transaction = _Transaction


def IsMissingParentRowError(error: Exception) -> bool:
  """Whether the error indicates a missing parent row of an interleaved table.

  PySpanner raises such failures without a dedicated exception type, so the
  error message has to be matched. Centralizing the check here keeps that
  brittleness in a single place.
  """
  return "Parent row for row [" in str(error)


def IsConstraintViolatedError(error: Exception, constraint_name: str) -> bool:
  """Whether the error indicates a violation of the given named constraint.

  See `IsMissingParentRowError` on why the error message is matched.
  """
  return constraint_name in str(error)

class Database:
  """A wrapper around the PySpanner class.

  The wrapper is supposed to streamline the usage of Spanner database through
  an abstraction that is much harder to misuse. The wrapper will run retryable
  queries through a transaction runner handling all brittle logic for the user.
  """

  _PYSPANNER_PARAM_REGEX = re.compile(r"@p\d+")

  def __init__(self, pyspanner: spanner_lib.Database, project_id: str) -> None:
    super().__init__()
    self._pyspanner = pyspanner
    self.project_id = project_id
  def _parametrize(self, query: str, names: Iterable[str]) -> str:
    match = self._PYSPANNER_PARAM_REGEX.search(query)
    if match is not None:
      raise ValueError(f"Query contains illegal sequence: {match.group(0)}")

    kwargs = {}
    for name in names:
      kwargs[name] = f"@{name}"

    return query.format(**kwargs)

  def _get_param_type(self, value):
    """
    Infers the Google Cloud Spanner type from a Python value.

    Args:
        value: The Python value whose Spanner type is to be inferred.

    Returns:
        A google.cloud.spanner_v1.types.Type object, or None if the type
        cannot be reliably inferred (e.g., for a standalone None value or
        an empty list).
    Raises:
        TypeError: Raised for any unsupported type or empty container value.
    """
    if value is None:
      # Cannot determine a specific Spanner type from a None value alone.
      # This indicates that the type is ambiguous without further schema
      # context.
      return None

    py_type = type(value)

    if py_type is int:
      return param_types.INT64
    elif py_type is float:
      return param_types.FLOAT64
    elif py_type is str:
      return param_types.STRING
    elif py_type is bool:
      return param_types.BOOL
    elif py_type is bytes:
      return param_types.BYTES
    elif py_type is datetime.date:
      return param_types.DATE
    elif py_type is datetime.datetime:
      # Note: Spanner TIMESTAMPs are stored in UTC. Ensure datetime objects
      # are timezone-aware (UTC) when writing data. This function only maps the
      # type.
      return param_types.TIMESTAMP
    elif py_type is decimal.Decimal:
      return param_types.NUMERIC
    elif py_type is list:
      if len(value) > 0:
        return param_types.Array(self._get_param_type(value[0]))
      else:
        raise TypeError(f"Empty value for Python type: {py_type.__name__} for Spanner type conversion.")
    else:
      # Potentially raise an error for unsupported types or return None
      # For a generic solution, raising an error for unknown types is often safer.
      raise TypeError(f"Unsupported Python type: {py_type.__name__} for Spanner type conversion.")

  def Transact(
      self,
      func: Callable[["Transaction"], _T],
      txn_tag: Optional[str] = None,
  ) -> _T:

    """Execute the given callback function in a Spanner transaction.

    Args:
      func: A transaction function to execute.
      txn_tag: Transaction tag to apply.

    Returns:
      The result of the transaction function executed.
    """
    return self._pyspanner.run_in_transaction(func, transaction_tag=txn_tag)

  def Mutate(
      self, func: Callable[["Mutation"], None], txn_tag: Optional[str] = None
  ) -> None:
    """Execute the given callback function in a Spanner mutation.

    Args:
      func: A mutation function to execute.
      txn_tag: Spanner transaction tag.
    """

    self.Transact(func, txn_tag=txn_tag)

  def Query(self, query: str, txn_tag: Optional[str] = None) -> Cursor:
    """Queries Spanner database using the given query string.

    Args:
      query: An SQL string.
      txn_tag: Spanner transaction tag.

    Returns:
      The rows of the query result.
    """
    # Results must be fully consumed before the snapshot context is exited:
    # on exit the session is returned to the pool and may be picked up by
    # another thread, while the streaming RPC of an unconsumed result set
    # would still be using it.
    with self._pyspanner.snapshot() as snapshot:
      results = snapshot.execute_sql(query, request_options={"request_tag": txn_tag})
      return list(results)

  def QuerySingle(self, query: str, txn_tag: Optional[str] = None) -> Row:
    """Queries PySpanner for a single row using the given query string.

    Args:
      query: An SQL string.
      txn_tag: Spanner transaction tag.

    Returns:
      A single row matching the query.

    Raises:
      NotFound: If the query did not return any results.
      ValueError: If the query yielded more than one result.
    """
    with self._pyspanner.snapshot() as snapshot:
      results = snapshot.execute_sql(query, request_options={"request_tag": txn_tag})
      return results.one()

  def ParamQuery(
      self, query: str, params: Mapping[str, Any],
      param_type: Optional[dict] = None, txn_tag: Optional[str] = None
  ) -> Cursor:
    """Queries PySpanner database using the given query string with params.

    The query string should specify parameters with the standard Python format
    placeholder syntax [1]. Note that parameters inside string literals in the
    query itself have to be escaped.

    Also, the query literal is not allowed to contain any '@p{idx}' strings
    inside as that would lead to an incorrect behaviour when evaluating the
    query. To prevent mistakes the function will raise an exception in such
    cases.

    [1]: https://docs.python.org/3/library/stdtypes.html#str.format

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      txn_tag: Spanner transaction tag.

    Returns:
      A cursor over the query results.

    Raises:
      ValueError: If the query contains disallowed sequences.
      KeyError: If some parameter is not specified.
    """
    query, param_type = self._PrepareParamQuery(query, params, param_type)

    with self._pyspanner.snapshot() as snapshot:
      results = snapshot.execute_sql(
          query,
          params=params,
          param_types=param_type,
          request_options={"request_tag": txn_tag}
      )
      return list(results)

  def _PrepareParamQuery(
      self, query: str, params: Mapping[str, Any],
      param_type: Optional[dict] = None
  ) -> Tuple[str, dict]:
    """Substitutes parameter placeholders and infers missing param types.

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      param_type: An optional dictionary with explicit parameter types. It is
        not modified; missing entries are inferred from the values.

    Returns:
      A tuple of the parametrized query and the complete param type mapping.
    """
    names, _ = collection.Unzip(params.items())
    query = self._parametrize(query, names)

    param_type = dict(param_type) if param_type else {}
    for key, value in params.items():
      if key not in param_type:
        try:
          param_type[key] = self._get_param_type(value)
        except TypeError as e:
          logging.warning(
              "Cannot infer Spanner type of param %r (%s), leaving it untyped.",
              key, e,
          )
          param_type[key] = None

    return query, param_type

  def ParamQuerySingle(
      self, query: str, params: Mapping[str, Any],
      param_type: Optional[dict] = None, txn_tag: Optional[str] = None
  ) -> Row:
    """Queries the database for a single row using with a query with params.

    See documentation for `ParamQuery` to learn more about the syntax of query
    parameters and other caveats.

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      txn_tag: Spanner transaction tag.

    Returns:
      A single result of running the query.

    Raises:
      NotFound: If the query did not return any results.
      ValueError: If the query yielded more than one result.
      ValueError: If the query contains disallowed sequences.
      KeyError: If some parameter is not specified.
    """
    query, param_type = self._PrepareParamQuery(query, params, param_type)

    with self._pyspanner.snapshot() as snapshot:
      results = snapshot.execute_sql(
          query,
          params=params,
          param_types=param_type,
          request_options={"request_tag": txn_tag}
      )
      return results.one()

  def ParamExecute(
      self, query: str, params: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Executes the given query with parameters against a Spanner database.

    Args:
      query: An SQL string with parameter placeholders.
      params: A dictionary mapping parameter name to a value.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.

    Raises:
      ValueError: If the query contains disallowed sequences.
      KeyError: If some parameter is not specified.
    """
    query, param_type = self._PrepareParamQuery(query, params)

    def param_execute(txn: Transaction):
      txn.execute_update(
          query,
          params=params,
          param_types=param_type,
          request_options={"request_tag": txn_tag},
      )

    self._pyspanner.run_in_transaction(param_execute)

  def ExecutePartitioned(
      self,
      query: str,
      params: Optional[Mapping[str, Any]] = None,
      param_type: Optional[dict] = None,
      txn_tag: Optional[str] = None,
  ) -> int:
    """Executes the given query as partitioned DML against a Spanner database.

    This is a more efficient variant of the `Execute` method, but it does not
    guarantee atomicity. See the official documentation on partitioned updates
    for more information [1].

    [1]: go/spanner-partitioned-dml

    Args:
      query: An SQL query string to execute, optionally with parameter
        placeholders (see `ParamQuery`).
      params: An optional dictionary mapping parameter name to a value.
      param_type: An optional dictionary with explicit parameter types.
      txn_tag: Spanner transaction tag.

    Returns:
      A lower bound of the number of rows modified.
    """
    if params:
      query, param_type = self._PrepareParamQuery(query, params, param_type)

    return self._pyspanner.execute_partitioned_dml(
        query,
        params=params,
        param_types=param_type,
        request_options={"request_tag": txn_tag},
    )

  def Insert(
      self, table: str, row: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Insert a row into the given table.

    Args:
      table: A table into which the row is to be inserted.
      row: A mapping from column names to column values of the row.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    columns, values = collection.Unzip(row.items())

    columns = list(columns)
    values = list(values)

    with self._pyspanner.batch(request_options={"request_tag": txn_tag}) as batch:
      batch.insert(
        table=table,
        columns=columns,
        values=[values]
      )

  def Update(
      self, table: str, row: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Updates a row in the given table.

    Args:
      table: A table in which the row is to be updated.
      row: A mapping from column names to column values of the row.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    columns, values = collection.Unzip(row.items())

    columns = list(columns)
    values = list(values)

    with self._pyspanner.batch(request_options={"request_tag": txn_tag}) as batch:
      batch.update(
        table=table,
        columns=columns,
        values=[values]
      )

  def InsertOrUpdate(
      self, table: str, row: Mapping[str, Any], txn_tag: Optional[str] = None
  ) -> None:
    """Insert or update a row into the given table within the transaction.

    Args:
      table: A table into which the row is to be inserted.
      row: A mapping from column names to column values of the row.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.
    """
    columns, values = collection.Unzip(row.items())

    columns = list(columns)
    values = list(values)

    with self._pyspanner.batch(request_options={"request_tag": txn_tag}) as batch:
      batch.insert_or_update(
        table=table,
        columns=columns,
        values=[values]
      )

  def Delete(
      self, table: str, key: Sequence[Any], txn_tag: Optional[str] = None
  ) -> None:
    """Deletes a specified row from the given table.

    Args:
      table: A table from which the row is to be deleted.
      key: A sequence of values denoting the key of the row to delete.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.

    Raises:
      ValueError: If the key is empty (a caller bug that would otherwise
        silently delete every row of the table).
    """
    if not key:
      raise ValueError(f"Empty key for deletion from table '{table}'")

    keyset = KeySet(keys=[key])
    with self._pyspanner.batch(request_options={"request_tag": txn_tag}) as batch:
      batch.delete(table, keyset)

  def DeleteWithPrefix(self, table: str, key_prefix: Sequence[Any],
                       txn_tag: Optional[str] = None) -> None:
    """Deletes a range of rows with common key prefix from the given table.

    Args:
      table: A table from which rows are to be deleted.
      key_prefix: A sequence of value denoting the prefix of the key of rows to delete.
      txn_tag: Spanner transaction tag.

    Returns:
      Nothing.

    Raises:
      ValueError: If the key prefix is empty (a caller bug that would
        otherwise silently delete every row of the table).
    """
    if not key_prefix:
      raise ValueError(f"Empty key prefix for deletion from table '{table}'")

    range = KeyRange(start_closed=key_prefix, end_closed=key_prefix)
    keyset = KeySet(ranges=[range])

    with self._pyspanner.batch(request_options={"request_tag": txn_tag}) as batch:
      batch.delete(table, keyset)

  def Read(
      self,
      table: str,
      key: Sequence[Any],
      cols: Sequence[str],
      txn_tag: Optional[str] = None
  ) -> Row:
    """Read a single row with the given key from the specified table.

    Args:
      table: A name of the table to read from.
      key: A key of the row to read.
      cols: Columns of the row to read.
      txn_tag: Spanner transaction tag.

    Returns:
      A mapping from columns to values of the read row.
    """
    keyset = KeySet(keys=[key])
    with self._pyspanner.snapshot() as snapshot:
      results = snapshot.read(
          table=table,
          columns=cols,
          keyset=keyset,
          request_options={"request_tag": txn_tag}
      )
      return results.one()

  def ReadSet(
      self,
      table: str,
      rows: KeySet,
      cols: Sequence[str],
      txn_tag: Optional[str] = None
  ) -> Cursor:
    """Read a set of rows from the specified table.

    Args:
      table: A name of the table to read from.
      rows: A set of keys specifying which rows to read.
      cols: Columns of the row to read.
      txn_tag: Spanner transaction tag.

    Returns:
      Mappings from columns to values of the rows read.
    """
    with self._pyspanner.snapshot() as snapshot:
      results = snapshot.read(
          table=table,
          columns=cols,
          keyset=rows,
          request_options={"request_tag": txn_tag}
      )
      return list(results)
