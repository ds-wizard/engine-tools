import pytest

from dsw.config.keys import (
    DEFAULT_TABLE_PREFIX,
    ConfigKeys,
    cast_bool,
    cast_optional_bool,
    cast_optional_float,
    cast_optional_int,
    cast_optional_str,
    cast_str,
    cast_table_prefix,
)


@pytest.mark.parametrize('value', ['true', 'True', 'TRUE', ' yes ', 'on', '1', True, 1])
def test_cast_bool_true(value):
    assert cast_bool(value) is True


@pytest.mark.parametrize('value', ['false', 'False', 'no', 'off', '0', '', 'nope', False, 0])
def test_cast_bool_false(value):
    assert cast_bool(value) is False


def test_cast_optional_bool():
    assert cast_optional_bool(None) is None
    assert cast_optional_bool('false') is False
    assert cast_optional_bool('true') is True


def test_cast_str_no_none_string():
    assert cast_str(None) == ''
    assert cast_str(True) == 'true'
    assert cast_str(False) == 'false'
    assert cast_str(42) == '42'
    assert cast_optional_str(None) is None
    assert cast_optional_str(False) == 'false'


def test_cast_optional_numbers_blank():
    assert cast_optional_int(None) is None
    assert cast_optional_int('') is None
    assert cast_optional_int('  ') is None
    assert cast_optional_int('100') == 100
    assert cast_optional_float(None) is None
    assert cast_optional_float('') is None
    assert cast_optional_float('0.5') == 0.5


def test_logging_var_names():
    assert ConfigKeys.logging.level.var_names == ['LOGGING_LEVEL']
    assert ConfigKeys.logging.global_level.var_names == ['LOGGING_GLOBAL_LEVEL']


def test_keys_container_includes_inherited_keys():
    class CustomKeys(ConfigKeys):
        pass

    base_paths = {'.'.join(key.yaml_path) for key in ConfigKeys}
    custom_paths = {'.'.join(key.yaml_path) for key in CustomKeys}
    assert base_paths
    assert base_paths <= custom_paths


@pytest.mark.parametrize('value', ['w_', 'x', '_x', 'dsw_wizard_', 'A1_'])
def test_cast_table_prefix_valid(value):
    assert cast_table_prefix(value) == value


def test_cast_table_prefix_blank_means_no_prefix():
    assert cast_table_prefix(None) == ''
    assert cast_table_prefix('') == ''
    assert cast_table_prefix('  ') == ''


def test_cast_table_prefix_strips_surrounding_whitespace():
    assert cast_table_prefix(' w_ ') == 'w_'


@pytest.mark.parametrize('value', ['1w_', 'w-', 'w;', 'w.x', 'w"', "w'", 'w_ x'])
def test_cast_table_prefix_invalid(value):
    with pytest.raises(ValueError, match='Invalid database table prefix'):
        cast_table_prefix(value)


def test_table_prefix_key_defaults():
    key = ConfigKeys.database.table_prefix
    assert key.yaml_path == ['database', 'tablePrefix']
    assert key.var_names == ['DATABASE_TABLE_PREFIX']
    assert key.default == DEFAULT_TABLE_PREFIX == 'w_'
