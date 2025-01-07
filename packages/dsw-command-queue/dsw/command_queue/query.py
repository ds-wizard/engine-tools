import enum


class CommandState(enum.Enum):
    NEW = 'NewPersistentCommandState'
    DONE = 'DonePersistentCommandState'
    ERROR = 'ErrorPersistentCommandState'
    IGNORE = 'IgnorePersistentCommandState'


class CommandQueries:

    def __init__(self, channel: str, component: str):
        self.channel = channel
        self.component = component

    def query_listen(self) -> str:
        return f'LISTEN persistent_command_channel__{self.channel};'

    def query_get_command(self, exp=2, interval='1 min') -> str:
        return f"""
            SELECT *
            FROM persistent_command
            WHERE component = '{self.component}'
              AND attempts < max_attempts
              AND state != '{CommandState.DONE.value}'
              AND state != '{CommandState.IGNORE.value}'
              AND (updated_at AT TIME ZONE 'UTC')
                    <
                  (%(now)s - ({exp} ^ attempts - 1) * INTERVAL '{interval}')
            ORDER BY attempts ASC, updated_at DESC
            LIMIT 1 FOR UPDATE SKIP LOCKED;
        """

    @staticmethod
    def query_command_error() -> str:
        return f"""
            UPDATE persistent_command
            SET attempts = %(attempts)s,
                last_error_message = %(error_message)s,
                state = '{CommandState.ERROR.value}',
                updated_at = %(updated_at)s
            WHERE uuid = %(uuid)s;
        """

    @staticmethod
    def query_command_error_stop() -> str:
        return f"""
            UPDATE persistent_command
            SET attempts = %(attempts)s,
                max_attempts = %(attempts)s,
                last_error_message = %(error_message)s,
                state = '{CommandState.ERROR}',
                updated_at = %(updated_at)s
            WHERE uuid = %(uuid)s;
        """

    @staticmethod
    def query_command_done() -> str:
        return f"""
            UPDATE persistent_command
            SET attempts = %(attempts)s,
                state = '{CommandState.DONE.value}',
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
