import pathlib
import tomlkit
import sys

ROOT = pathlib.Path(__file__).parent.parent
PKGS = ROOT / 'packages'


def project_files() -> list[pathlib.Path]:
    """All pyproject.toml files that carry the project version.

    The workspace root is included: it is not published, but CONTRIBUTING.md
    requires consistent versioning and scripts/check-release.py asserts it.
    Keep this list in sync with check-release.py.
    """
    return [ROOT / 'pyproject.toml', *sorted(PKGS.glob('*/pyproject.toml'))]


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: version.py <version>')
        sys.exit(1)
    version_tag = sys.argv[1]

    for toml_file in project_files():
        toml_data = tomlkit.loads(toml_file.read_text(encoding='utf-8'))

        toml_data['project']['version'] = version_tag
        # The workspace root declares no runtime dependencies to re-pin
        deps = toml_data['project'].get('dependencies')
        if deps is not None:
            for i in range(len(deps)):
                dep = deps[i]
                if dep.startswith('dsw-') and '==' in dep:
                    dep_parts = dep.split('==')
                    deps[i] = f'{dep_parts[0]}=={version_tag}'

        toml_file.write_text(tomlkit.dumps(toml_data), encoding='utf-8')
        print(f'{toml_file.relative_to(ROOT)}: {version_tag}')
