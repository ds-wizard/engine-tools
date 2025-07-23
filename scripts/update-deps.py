import pathlib
import shutil
import subprocess
import venv

ENC = 'utf-8'


def run_update(root_dir: pathlib.Path):
    _update_root_requirements(root_dir)
    _update_packages(root_dir)

def _update_root_requirements(root_dir: pathlib.Path):
    env_dir = root_dir / 'env-deps'
    pip = env_dir / 'bin' / 'pip'
    pip_upgrade = env_dir / 'bin' / 'pip-upgrade'
    requirements_file = root_dir / 'requirements.txt'
    reqs = requirements_file.read_text(ENC)
    reqs.replace('==', '>=')
    requirements_file.write_text(reqs, ENC)
    venv.create(
        env_dir=env_dir,
        system_site_packages=False,
        clear=True,
        with_pip=True,
    )
    p = subprocess.Popen(
        args=[pip, 'install', '-U', 'setuptools'],
    )
    p.wait()
    p = subprocess.Popen(
        args=[pip, 'install', 'pip-upgrader'],
    )
    p.wait()
    p = subprocess.Popen(
        args=[pip_upgrade, requirements_file.as_posix()],
    )
    p.wait()
    shutil.rmtree(env_dir)

def _update_packages(root_dir: pathlib.Path):
    requirements_file = root_dir / 'requirements.txt'
    packages_dir = root_dir / 'packages'
    deps = _load_deps(requirements_file)
    for path in packages_dir.rglob('**/requirements.txt'):
        _update_pkg_requirements(path, deps)
    for path in packages_dir.rglob('**/requirements.test.txt'):
        _update_pkg_requirements(path, deps)

def _update_pkg_requirements(requirements_file: pathlib.Path, deps: dict[str, str]):
    lines = []
    for line in requirements_file.read_text(ENC).splitlines():
        parts = line.split('==')
        if len(parts) != 2:
            continue
        dep = parts[0]
        ver = deps.get(dep, parts[1])
        lines.append(f'{dep}=={ver}')
    lines.append('')
    requirements_file.write_text('\n'.join(lines), ENC)

def _load_deps(requirements_file: pathlib.Path) -> dict[str, str]:
    result = {}
    for line in requirements_file.read_text(ENC).splitlines():
        parts = line.split('==')
        if len(parts) == 2:
            result[parts[0]] = parts[1]
    return result


if __name__ == '__main__':
    run_update(pathlib.Path(__file__).parent.parent)
