from __future__ import annotations

import enum


# Savepoint wrapping the actual work of a command, so partial changes made by
# a failed job are not committed together with its error record
JOB_SAVEPOINT = 'dsw_command_job'


class CommandState(enum.Enum):
    NEW = 'NewPersistentCommandState'
    DONE = 'DonePersistentCommandState'
    ERROR = 'ErrorPersistentCommandState'
    IGNORE = 'IgnorePersistentCommandState'


class CommandQueries:

    def __init__(self, channel: str):
        self.channel = channel

    def query_listen(self) -> str:
        return f'LISTEN persistent_command_channel__{self.channel};'

    @staticmethod
    def query_get_command() -> str:
        # The backoff is measured from updated_at (set whenever an attempt
        # starts or finishes), not from created_at: with created_at the
        # exponential term would be just an absolute age threshold that any
        # older command satisfies for all values of attempts at once.
        return """
            SELECT *
            FROM persistent_command
            WHERE component = %(component)s
              AND attempts < max_attempts
              AND state != 'DonePersistentCommandState'
              AND state != 'IgnorePersistentCommandState'
              AND updated_at < (%(now)s - (2 ^ attempts - 1) * INTERVAL '1 min')
            ORDER BY attempts ASC, created_at ASC
            LIMIT 1 FOR UPDATE SKIP LOCKED;
        """

    @staticmethod
    def query_lock_command() -> str:
        return """
            SELECT uuid
            FROM persistent_command
            WHERE uuid = %(uuid)s
            LIMIT 1 FOR UPDATE NOWAIT;
        """

    @staticmethod
    def query_terminate_backend() -> str:
        return 'SELECT pg_terminate_backend(%(pid)s);'

    @staticmethod
    def query_savepoint() -> str:
        return f'SAVEPOINT {JOB_SAVEPOINT};'

    @staticmethod
    def query_rollback_to_savepoint() -> str:
        return f'ROLLBACK TO SAVEPOINT {JOB_SAVEPOINT};'

    @staticmethod
    def query_command_error() -> str:
        return """
            UPDATE persistent_command
            SET attempts = %(attempts)s,
                last_error_message = %(error_message)s,
                state = 'ErrorPersistentCommandState',
                updated_at = %(updated_at)s
            WHERE uuid = %(uuid)s;
        """

    @staticmethod
    def query_command_error_stop() -> str:
        return """
            UPDATE persistent_command
            SET attempts = %(attempts)s,
                max_attempts = %(attempts)s,
                last_error_message = %(error_message)s,
                state = 'ErrorPersistentCommandState',
                updated_at = %(updated_at)s
            WHERE uuid = %(uuid)s;
        """

    @staticmethod
    def query_command_done() -> str:
        return """
            UPDATE persistent_command
            SET attempts = %(attempts)s,
                state = 'DonePersistentCommandState',
                updated_at = %(updated_at)s
            WHERE uuid = %(uuid)s;
        """

    @staticmethod
    def query_command_start() -> str:
        return """
            UPDATE persistent_command
            SET attempts = %(attempts)s,
                updated_at = %(updated_at)s
            WHERE uuid = %(uuid)s;
        """
