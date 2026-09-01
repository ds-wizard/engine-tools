from dsw.config.model import (
    MASKED_VALUE,
    AWSConfig,
    DatabaseConfig,
    GeneralConfig,
    S3Config,
    SentryConfig,
)


def test_database_config_masks_connection_string():
    cfg = DatabaseConfig(
        connection_string='postgresql://user:secretPassword@db:5432/dsw',
        connection_timeout=30000,
        queue_timeout=180,
    )
    result = str(cfg)
    assert 'secretPassword' not in result
    assert f'- connection_string = {MASKED_VALUE} [str]' in result
    assert '- connection_timeout = 30000 [int]' in result


def test_s3_config_masks_password():
    cfg = S3Config(
        url='http://minio:9000',
        username='minio',
        password='minioPassword',
        bucket='engine-wizard',
        region='eu-central-1',
    )
    result = str(cfg)
    assert 'minioPassword' not in result
    assert '- username = minio [str]' in result


def test_general_config_masks_secret():
    cfg = GeneralConfig(environment='Test', client_url='http://localhost', secret='mySecret')
    result = str(cfg)
    assert 'mySecret' not in result
    assert '- environment = Test [str]' in result


def test_sentry_config_masks_dsn():
    cfg = SentryConfig(
        enabled=True,
        workers_dsn='https://token@sentry.io/1',
        traces_sample_rate=None,
        max_breadcrumbs=None,
        environment='production',
    )
    result = str(cfg)
    assert 'token' not in result
    assert '- enabled = True [bool]' in result


def test_aws_config_masks_credentials():
    cfg = AWSConfig(access_key_id='keyId', secret_access_key='secretKey', region='eu-central-1')
    result = str(cfg)
    assert 'keyId' not in result
    assert 'secretKey' not in result
    assert '- region = eu-central-1 [str]' in result


def test_unset_secret_is_not_masked():
    cfg = AWSConfig(access_key_id=None, secret_access_key=None, region=None)
    result = str(cfg)
    assert MASKED_VALUE not in result
    assert '- access_key_id = None [NoneType]' in result
