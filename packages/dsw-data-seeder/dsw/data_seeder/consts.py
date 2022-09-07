PROG_NAME = 'dsw-seeder'
VERSION = '3.15.0'
NULL_UUID = '00000000-0000-0000-0000-000000000000'

LOGGER_NAME = 'DSW_DATA_SEEDER'
DEFAULT_ENCODING = 'utf-8'
DEFAULT_MIMETYPE = 'application/octet-stream'
DEFAULT_PLACEHOLDER = '<<|APP-ID|>>'

CMD_COMPONENT = 'data_seeder'
CMD_CHANNEL = 'data_seeder'


class CommandState:
    NEW = 'NewPersistentCommandState'
    DONE = 'DonePersistentCommandState'
    ERROR = 'ErrorPersistentCommandState'
    IGNORE = 'IgnorePersistentCommandState'


class Queries:

    LISTEN = f'LISTEN persistent_command_channel__{CMD_CHANNEL};'

    SELECT_CMD = f"""
        SELECT *
        FROM persistent_command
        WHERE component = '{CMD_COMPONENT}'
          AND attempts < max_attempts
          AND state != '{CommandState.DONE}'
          AND state != '{CommandState.IGNORE}'
          AND (updated_at AT TIME ZONE 'UTC') < (%(now)s - (2 ^ attempts - 1) * INTERVAL '1 min')
        ORDER BY attempts ASC, updated_at DESC
        LIMIT 1 FOR UPDATE SKIP LOCKED;
    """

    UPDATE_CMD_ERROR = f"""
        UPDATE persistent_command
        SET attempts = %(attempts)s,
            last_error_message = %(error_message)s,
            state = '{CommandState.ERROR}',
            updated_at = %(updated_at)s
        WHERE uuid = %(uuid)s;
    """

    UPDATE_CMD_DONE = f"""
        UPDATE persistent_command
        SET attempts = %(attempts)s,
            state = '{CommandState.DONE}',
            updated_at = %(updated_at)s
        WHERE uuid = %(uuid)s;
    """
