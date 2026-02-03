import enum


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

    def query_get_command(self) -> str:
        return """
            SELECT *
            FROM persistent_command
            WHERE component = %(component)s
              AND attempts < max_attempts
              AND state != 'DonePersistentCommandState'
              AND state != 'IgnorePersistentCommandState'
              AND (created_at AT TIME ZONE 'UTC')
                    <
                  (%(now)s - (2 ^ attempts - 1) * INTERVAL '1 min')
            ORDER BY attempts ASC, updated_at DESC
            LIMIT 1 FOR UPDATE SKIP LOCKED;
        """

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
