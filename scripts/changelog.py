import pathlib
import sys

ROOT = pathlib.Path(__file__).parent.parent
PKGS = ROOT / 'packages'
INFO = 'Released for version consistency with other DSW tools.'


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: version.py <prev-version> <next-version>')
        sys.exit(1)
    prev_version = sys.argv[1]
    next_version = sys.argv[2]

    for changelog_file in PKGS.rglob('*/CHANGELOG.md'):
        changelog = changelog_file.read_text(encoding='utf-8')

        changelog = changelog.replace(
            '## [Unreleased]\n',
            f'## [Unreleased]\n\n\n## [{next_version}]\n'
        )
        changelog = changelog.replace(
            f'\n\n## [{prev_version}]\n',
            f'\n## [{prev_version}]\n'
        )
        changelog = changelog.replace(
            f'[{prev_version}]: /../../tree/v{prev_version}\n',
            f'[{prev_version}]: /../../tree/v{prev_version}\n'
            f'[{next_version}]: /../../tree/v{next_version}\n'
        )
        changelog = changelog.replace(
            f'## [{next_version}]\n\n## [{prev_version}]',
            f'## [{next_version}]\n\n{INFO}\n\n## [{prev_version}]',
        )

        new_changelog_file = changelog_file.parent / 'CHANGELOG.new.md'
        new_changelog_file.write_text(changelog, encoding='utf-8')
