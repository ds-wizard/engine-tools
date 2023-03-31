import pathlib
import tomlkit
import sys

ROOT = pathlib.Path(__file__).parent.parent
PKGS = ROOT / 'packages'


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: version.py <version>')
        sys.exit(1)
    version_tag = sys.argv[1]

    for toml_file in PKGS.rglob('*/pyproject.toml'):
        toml_data = tomlkit.loads(toml_file.read_text(encoding='utf-8'))

        toml_data['project']['version'] = version_tag
        for i in range(len(toml_data['project']['dependencies'])):
            dep = toml_data['project']['dependencies'][i]
            if dep.startswith('dsw-') and '==' in dep:
                dep_parts = dep.split('==')
                dep = f'{dep_parts[0]}=={version_tag}'
                toml_data['project']['dependencies'][i] = dep

        toml_file.write_text(tomlkit.dumps(toml_data), encoding='utf-8')
