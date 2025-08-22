import configparser
import dataclasses
import os
import pathlib

import dotenv

from .consts import DEFAULT_ENCODING


def _rectify_api_url(api_url: str | None) -> str:
    if not api_url or not isinstance(api_url, str):
        return ''
    return api_url.rstrip('/')


def _rectify_api_key(api_key: str | None) -> str:
    if not api_key or not isinstance(api_key, str):
        return ''
    return api_key.strip()


@dataclasses.dataclass
class TDKWizardEnv:
    api_url: str
    api_key: str

    def rectify(self):
        self.api_url = _rectify_api_url(self.api_url)
        self.api_key = _rectify_api_key(self.api_key)


class TDKConfig:
    LOCAL_CONFIG = '_local'
    HOME_CONFIG = pathlib.Path.home() / '.dsw-tdk' / 'config.cfg'

    def __init__(self):
        self.shared_envs = {}  # type: dict[str, TDKWizardEnv]
        self.local_env = TDKWizardEnv(
            api_url='',
            api_key='',
        )
        self.current_env_name = self.LOCAL_CONFIG
        self.default_env_name = None  # type: str | None

    def load_dotenv(self, path: pathlib.Path):
        try:
            if path.exists():
                dotenv.load_dotenv(path)
        except Exception as e:
            print(f"Error loading .env file: {e}")
        api_url = os.getenv('DSW_API_URL', '')
        api_key = os.getenv('DSW_API_KEY', '')

        if not api_url or not api_key:
            return

        self.current_env_name = self.LOCAL_CONFIG
        self.local_env = TDKWizardEnv(
            api_url=api_url,
            api_key=api_key,
        )
        self.local_env.rectify()

    def load_home_config(self):
        config_path = self.HOME_CONFIG
        if not config_path.exists():
            return

        config = configparser.ConfigParser()
        config.read(config_path)
        for section in config.sections():
            if section == 'default':
                self.default_env_name = config.get(section, 'env', fallback=None)
            elif section.startswith('env:'):
                env_name = section[4:]
                if env_name not in self.shared_envs:
                    self.shared_envs[env_name] = TDKWizardEnv(
                        api_url=config.get(section, 'api_url', fallback=''),
                        api_key=config.get(section, 'api_key', fallback=''),
                    )
                    self.shared_envs[env_name].rectify()
        if self.default_env_name is not None:
            self.current_env_name = self.default_env_name

    @property
    def env(self) -> TDKWizardEnv:
        if self.current_env_name == self.LOCAL_CONFIG:
            return self.local_env
        return self.shared_envs[self.current_env_name]

    @property
    def has_api_url(self) -> bool:
        return self.env.api_url != ''

    def set_api_url(self, api_url: str):
        self.env.api_url = _rectify_api_url(api_url)

    @property
    def has_api_key(self) -> bool:
        return self.env.api_key != ''

    def set_api_key(self, api_key: str):
        self.env.api_key = _rectify_api_key(api_key)

    def use_local_env(self):
        self.current_env_name = self.LOCAL_CONFIG

    def switch_current_env(self, env_name: str | None):
        if env_name not in self.shared_envs:
            raise ValueError(f'Environment "{env_name}" does not exist')
        self.current_env_name = env_name

    @property
    def is_default_env(self) -> bool:
        return self.current_env_name == self.default_env_name

    @property
    def env_names(self) -> list[str]:
        return sorted(env_name for env_name in self.shared_envs)

    def add_shared_env(self, name: str, api_url: str, api_key: str):
        if name == self.LOCAL_CONFIG:
            raise ValueError(f'Environment name "{self.LOCAL_CONFIG}" is reserved')
        if name in self.shared_envs:
            raise ValueError(f'Environment "{name}" already exists')
        self.shared_envs[name] = TDKWizardEnv(
            api_url=api_url,
            api_key=api_key,
        )

    def persist(self, force: bool):
        output = self.HOME_CONFIG
        if output.exists() and not force:
            raise FileExistsError(f'File {output.as_posix()} already exists (not forced)')
        if not output.parent.exists():
            output.parent.mkdir(parents=True, exist_ok=True)

        config = configparser.ConfigParser()
        config.add_section('default')
        if self.default_env_name:
            config.set('default', 'env', self.default_env_name)

        for env_name, env in self.shared_envs.items():
            section_name = f'env:{env_name}'
            config.add_section(section_name)
            config.set(section_name, 'api_url', env.api_url)
            config.set(section_name, 'api_key', env.api_key)

        with open(output, 'w', encoding=DEFAULT_ENCODING) as configfile:
            config.write(configfile)


CONFIG = TDKConfig()
