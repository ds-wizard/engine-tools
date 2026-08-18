import pytest

from dsw.config.keys import ConfigKeys


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Make tests independent of the ambient environment."""
    for key in ConfigKeys:
        for var_name in key.var_names:
            monkeypatch.delenv(var_name, raising=False)
            monkeypatch.delenv(f'DSW_{var_name}', raising=False)
