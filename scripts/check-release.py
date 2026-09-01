"""Assert that a release tag agrees with every project version.

Tags are written as ``v<version>`` and normalised per PEP 440, so the tag
``v4.33.0-rc.1`` is expected to match the package version ``4.33.0rc1``.

Covers the workspace root as well as every package, matching what
scripts/version.py writes. Keep the two file lists in sync.

Usage: check-release.py <tag>
"""
import pathlib
import sys
import tomllib

from packaging.version import InvalidVersion, Version

ROOT = pathlib.Path(__file__).parent.parent
PKGS = ROOT / 'packages'


def parse(raw: str) -> Version | None:
    try:
        return Version(raw)
    except InvalidVersion:
        return None


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: check-release.py <tag>')
        return 1

    tag = sys.argv[1]
    expected = parse(tag.removeprefix('v'))
    if expected is None:
        print(f'::error::Release tag "{tag}" is not a valid PEP 440 version')
        return 1

    mismatches = []
    checked = 0
    for toml_file in [ROOT / 'pyproject.toml', *sorted(PKGS.glob('*/pyproject.toml'))]:
        data = tomllib.loads(toml_file.read_text(encoding='utf-8'))
        name = data['project']['name']
        actual = data['project']['version']
        checked += 1

        if parse(actual) == expected:
            print(f'  OK    {name}: {actual}')
        else:
            mismatches.append(name)
            print(f'  FAIL  {name}: {actual} (expected {expected})')

    if checked <= 1:
        print(f'::error::No packages found under {PKGS}')
        return 1

    if mismatches:
        print(
            f'::error::Release tag "{tag}" (version {expected}) does not match '
            f'{len(mismatches)} of {checked} project versions: '
            f'{", ".join(mismatches)}'
        )
        return 1

    print(f'All {checked} project versions match release tag "{tag}" ({expected})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
