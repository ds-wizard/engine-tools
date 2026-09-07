"""Assert that a release tag is safe to publish from.

There are no version numbers in the repository any more: every package version
is derived from the git tag by uv-dynamic-versioning. That removes the old
"do all ten pyproject.toml agree with the tag?" check and replaces it with the
one thing that can still go wrong, silently and irreversibly.

``uv build`` from a checkout where the tag is not reachable does not fail. It
produces ``0.0.0.post<N>.dev0+<sha>`` and publishes it happily. A shallow
checkout (``actions/checkout`` defaults to ``fetch-depth: 1``) is exactly such
a checkout. So before anything is uploaded to PyPI, assert that:

1. the tag is a valid PEP 440 version once ``v`` is stripped, and
2. the tag actually points at HEAD in this checkout, so the version the build
   backend derives is the version being released.

Tags are written as ``v<version>`` and normalised per PEP 440, so the tag
``v4.33.0-rc.1`` corresponds to the package version ``4.33.0rc1``.

Usage: check-release.py <tag>
"""
import pathlib
import subprocess
import sys

from packaging.version import InvalidVersion, Version

ROOT = pathlib.Path(__file__).parent.parent


def parse(raw: str) -> Version | None:
    try:
        return Version(raw)
    except InvalidVersion:
        return None


def git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ['git', *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return result.stdout.strip()


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: check-release.py <tag>')
        return 1

    tag = sys.argv[1]
    expected = parse(tag.removeprefix('v'))
    if expected is None:
        print(f'::error::Release tag "{tag}" is not a valid PEP 440 version')
        return 1
    print(f'  OK    tag "{tag}" parses as version {expected}')

    tag_sha = git('rev-list', '-n', '1', tag)
    if tag_sha is None:
        print(
            f'::error::Tag "{tag}" is not present in this checkout. A shallow '
            f'checkout would build 0.0.0.post*.dev* instead of {expected} - '
            f'use fetch-depth: 0.'
        )
        return 1

    head_sha = git('rev-parse', 'HEAD')
    if head_sha is None:
        print('::error::Not a git repository - cannot verify the release tag')
        return 1

    if tag_sha != head_sha:
        print(
            f'::error::Tag "{tag}" points at {tag_sha[:8]} but HEAD is '
            f'{head_sha[:8]}. Release from the tagged commit, or the built '
            f'version will not be {expected}.'
        )
        return 1
    print(f'  OK    tag "{tag}" is on HEAD ({head_sha[:8]})')

    # The build backend sees the same repository this script does, so if the
    # tag is exactly on HEAD the derived version is the tag's version.
    described = git('describe', '--tags', '--exact-match', 'HEAD')
    if described is None:
        print(
            f'::error::git describe --exact-match found no tag on HEAD, so '
            f'the build would not derive {expected}'
        )
        return 1
    print(f'  OK    git describe --exact-match: {described}')

    print(f'Release tag "{tag}" ({expected}) is safe to build and publish')
    return 0


if __name__ == '__main__':
    sys.exit(main())
