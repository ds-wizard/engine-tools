import importlib
import pkgutil
import sys


def import_all(top_level_module: str):
    pkg = importlib.import_module(top_level_module)
    errors = []
    for mod in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + '.'):
        if mod.name.endswith('__main__'):
            continue
        try:
            importlib.import_module(mod.name)
            print(f'Imported: {mod.name}')
        except Exception as e:
            errors.append((mod.name, e))
    if errors:
        print('-'*60)
        print('FAILED imports:')
        for name, err in errors:
            print(f'  {name}: {err}')
        raise SystemExit(1)
    print('-'*60)
    print(f'All modules in {top_level_module} imported successfully')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python import-package.py <package_name>')
        sys.exit(1)
    package_name = sys.argv[1]
    top_level_module = package_name.replace('-', '_')
    if top_level_module.startswith('dsw_'):
        top_level_module = top_level_module.replace('dsw_', 'dsw.')
    import_all(top_level_module)
