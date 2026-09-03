from __future__ import annotations

import enum


# Savepoint wrapping the actual work of a command, so partial changes made by
# a failed job are not committed together with its error record
JOB_SAVEPOINT = 'dsw_command_job'

# The command queries are templates: "{p}" stands for the configured table
# prefix (table names cannot be passed as query parameters). Note that the
# notification channel is not derived from the table name, so it is not
# prefixed.
QUERY_LISTEN = 'LISTEN persistent_command_channel__{channel};'

# The backoff is measured from updated_at (set whenever an attempt
# starts or finishes), not from created_at: with created_at the
# exponential term would be just an absolute age threshold that any
# older command satisfies for all values of attempts at once.
QUERY_GET_COMMAND = """
    SELECT *
    FROM {p}persistent_command
    WHERE component = %(component)s
      AND attempts < max_attempts
      AND state != 'DonePersistentCommandState'
      AND state != 'IgnorePersistentCommandState'
      AND updated_at < (%(now)s - (2 ^ attempts - 1) * INTERVAL '1 min')
    ORDER BY attempts ASC, created_at ASC
    LIMIT 1 FOR UPDATE SKIP LOCKED;
"""

QUERY_LOCK_COMMAND = """
    SELECT uuid
    FROM {p}persistent_command
    WHERE uuid = %(uuid)s
    LIMIT 1 FOR UPDATE NOWAIT;
"""

QUERY_COMMAND_ERROR = """
    UPDATE {p}persistent_command
    SET attempts = %(attempts)s,
        last_error_message = %(error_message)s,
        state = 'ErrorPersistentCommandState',
        updated_at = %(updated_at)s
    WHERE uuid = %(uuid)s;
"""

QUERY_COMMAND_ERROR_STOP = """
    UPDATE {p}persistent_command
    SET attempts = %(attempts)s,
        max_attempts = %(attempts)s,
        last_error_message = %(error_message)s,
        state = 'ErrorPersistentCommandState',
        updated_at = %(updated_at)s
    WHERE uuid = %(uuid)s;
"""

QUERY_COMMAND_DONE = """
    UPDATE {p}persistent_command
    SET attempts = %(attempts)s,
        state = 'DonePersistentCommandState',
        updated_at = %(updated_at)s
    WHERE uuid = %(uuid)s;
"""

QUERY_COMMAND_START = """
    UPDATE {p}persistent_command
    SET attempts = %(attempts)s,
        updated_at = %(updated_at)s
    WHERE uuid = %(uuid)s;
"""


class CommandState(enum.Enum):
    NEW = 'NewPersistentCommandState'
    DONE = 'DonePersistentCommandState'
    ERROR = 'ErrorPersistentCommandState'
    IGNORE = 'IgnorePersistentCommandState'


class CommandQueries:

    def __init__(self, channel: str, table_prefix: str):
        self.channel = channel
        self.table_prefix = table_prefix

    def _q(self, query: str) -> str:
        return query.format(p=self.table_prefix)

    def query_listen(self) -> str:
        return QUERY_LISTEN.format(channel=self.channel)

    def query_get_command(self) -> str:
        return self._q(QUERY_GET_COMMAND)

    def query_lock_command(self) -> str:
        return self._q(QUERY_LOCK_COMMAND)

    @staticmethod
    def query_terminate_backend() -> str:
        return 'SELECT pg_terminate_backend(%(pid)s);'

    @staticmethod
    def query_savepoint() -> str:
        return f'SAVEPOINT {JOB_SAVEPOINT};'

    @staticmethod
    def query_rollback_to_savepoint() -> str:
        return f'ROLLBACK TO SAVEPOINT {JOB_SAVEPOINT};'

    def query_command_error(self) -> str:
        return self._q(QUERY_COMMAND_ERROR)

    def query_command_error_stop(self) -> str:
        return self._q(QUERY_COMMAND_ERROR_STOP)

    def query_command_done(self) -> str:
        return self._q(QUERY_COMMAND_DONE)

    def query_command_start(self) -> str:
        return self._q(QUERY_COMMAND_START)
