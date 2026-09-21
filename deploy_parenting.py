r"""Local pack -> SCP -> Ubuntu systemd install. Never uploads anything by itself.

Windows (stop bot/web/scheduler first):
  .venv\Scripts\python.exe deploy_parenting.py pack --stopped
Ubuntu:
  sudo python3 deploy_parenting.py install parenting-server-transfer.zip
  sudo python3 deploy_parenting.py status

The transfer ZIP contains private data and credentials. Keep it off GitHub/chat.
Only first installation is supported. Existing deployed data is never replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

APP = Path('/opt/parenting-agent')
DATA = Path('/var/lib/parenting-agent')
ACCOUNT = 'parenting-agent'
SERVICES = ['parenting-web', 'parenting-bot', 'parenting-scheduler']
REQUIRED = ['baby.py', 'storage.py', 'router.py', 'feishu_bot.py',
            'streamlit_app.py', 'run_scheduler.py', 'family_members.py',
            'requirements.txt', 'agent_v2/service.py', 'family_features/media.py',
            'family_features/dashboard.py', 'family_features/scheduler.py',
            'knowledge/healthy_parenting_guide_0_3.pdf']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def regular_files(root):
    """No symlinks/junctions to material outside the selected directory."""
    if not root.exists():
        return
    for path in sorted(root.rglob('*')):
        require(not path.is_symlink() and not getattr(path, 'is_junction', lambda: False)(),
                '符号链接/目录联接不自动迁移：' + str(path))
        if path.is_file() and '__pycache__' not in path.parts:
            require(path.resolve().is_relative_to(root.resolve()), '文件越出目录。')
            yield path


def collect(project):
    from dotenv import dotenv_values
    for name in REQUIRED:
        require((project / name).is_file(), '项目缺少文件：' + name)
    env_path = project / '.env'
    require(env_path.is_file(), '找不到项目 .env，请先完成本地配置。')
    values = dotenv_values(env_path, encoding='utf-8-sig')
    for key in ['DEEPSEEK_API_KEY', 'FEISHU_APP_ID', 'FEISHU_APP_SECRET',
                'VISION_API_KEY', 'VISION_BASE_URL', 'VISION_MODEL']:
        require(bool(values.get(key)), key + ' 未写入项目 .env。')
    require(len(values.get('WEB_PASSWORD') or '') >= 16, 'WEB_PASSWORD 至少16位。')
    require(bool(values.get('FEISHU_ALLOWED_CHAT_IDS')), '请先配置 FEISHU_ALLOWED_CHAT_IDS。')
    data = Path(os.environ.get('PARENTING_DATA_DIR') or values.get('PARENTING_DATA_DIR') or 'data')
    if not data.is_absolute():
        data = project / data
    data = data.resolve()
    require(data.is_dir() and data != project and not project.is_relative_to(data),
            '数据目录不存在或范围过大，停止打包。')
    require((data / 'baby.json').is_file(), '找不到真实 baby.json，拒绝迁移示例档案。')
    records = json.loads((data / 'baby.json').read_text(encoding='utf-8-sig'))
    require(isinstance(records, dict), 'baby.json 必须为JSON对象。')
    for item in records.get('memories', []):
        if item.get('_deleted_at'):
            continue
        for photo in item.get('photos', []):
            parts = photo.replace('\\', '/').split('/')
            require('uploads' in parts and '..' not in parts, '档案中有不合法照片路径。')
            source = data.joinpath('uploads', *parts[parts.index('uploads') + 1:])
            require(source.is_file() and source.resolve().is_relative_to(data / 'uploads'),
                    '有照片文件缺失，请先运行 verify_features.py 排查。')
    files = {'app/.env': env_path}
    for path in sorted(project.glob('*.py')):
        if not path.name.startswith(('test_', 'manual_', 'debug_')) and path.name != 'conftest.py':
            files['app/' + path.name] = path
    for folder in ['agent_v2', 'family_features', 'query', 'rag', 'knowledge']:
        for path in regular_files(project / folder):
            if path.suffix.lower() in {'.py', '.pdf', '.txt', '.md', '.json'}:
                files['app/' + path.relative_to(project).as_posix()] = path
    files['app/requirements.txt'] = project / 'requirements.txt'
    example = project / 'data/baby.example.json'
    if example.is_file():
        files['app/data/baby.example.json'] = example
    # All data/state is included: photos, audit, memberships, scheduler receipts.
    # SQLite is only a mutex here; idle lock files can be recreated on the server.
    for path in regular_files(data):
        if '.lock.sqlite3' not in path.name:
            files['data/' + path.relative_to(data).as_posix()] = path
    for path in files.values():
        require(not path.is_symlink(), '拒绝打包符号链接。')
    return files, data


def pack(project, output, stopped):
    require(stopped, '先关闭本地飞书、网页和定时服务，再加 --stopped 运行。')
    project = Path(project).resolve()
    output = Path(output).resolve() if output else project.parent / 'parenting-server-transfer.zip'
    require(not output.exists(), '迁移包已存在。请先将旧包改名留作备份，再重新打包。')
    files, data = collect(project)
    require(not output.is_relative_to(data), '迁移包不能保存在数据目录里。')
    require(not output.is_relative_to(project), '迁移包应保存在项目目录之外。')
    output.parent.mkdir(parents=True, exist_ok=True)
    snapshots = {name: (p.stat().st_size, p.stat().st_mtime_ns, digest(p)) for name, p in files.items()}
    fd, temp = tempfile.mkstemp(prefix='parenting-transfer-', suffix='.zip', dir=output.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, path in files.items():
                archive.write(path, name)
            archive.writestr('manifest.json', json.dumps({
                'format': 1, 'files': {name: snapshot[2] for name, snapshot in snapshots.items()}
            }, ensure_ascii=False, indent=2))
        require(set(collect(project)[0]) == set(files), '打包期间文件清单发生变化，请停止程序后重试。')
        for name, path in files.items():
            require((path.stat().st_size, path.stat().st_mtime_ns, digest(path)) == snapshots[name],
                    '打包期间文件有变化，请停止本地程序后重试。')
        verify_archive(Path(temp))
        os.chmod(temp, 0o600)
        os.replace(temp, output)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print('迁移包已生成：' + str(output))
    print(f'包含 {len(files)} 个文件；真实档案、照片、推送设置和发送状态已包含。')
    print('此包含密钥和家庭数据，只上传到你自己的服务器，不发到聊天或GitHub。')
    print('服务器开始运行后，请保持电脑上的三个服务关闭，避免产生两份独立档案。')


def verify_archive(path):
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)), '压缩包含重复路径。')
        require('manifest.json' in names, '迁移包缺少清单。')
        require(archive.getinfo('manifest.json').file_size < 8 * 1024 * 1024, '清单异常。')
        manifest = json.loads(archive.read('manifest.json'))
        require(manifest.get('format') == 1 and isinstance(manifest.get('files'), dict), '清单格式不支持。')
        expected = manifest['files']
        require(set(names) == set(expected) | {'manifest.json'}, '包内文件与清单不符。')
        require(all('app/' + f in expected for f in REQUIRED), '迁移包缺少核心代码。')
        require('app/.env' in expected and 'data/baby.json' in expected, '缺少配置或真实档案。')
        for item in archive.infolist():
            name = item.filename
            parts = PurePosixPath(name).parts
            require(name and '\\' not in name and ':' not in name and not name.startswith('/')
                    and '..' not in parts and str(PurePosixPath(name)) == name,
                    '压缩包包含不安全路径。')
            require(name == 'manifest.json' or parts[0] in {'app', 'data'}, '压缩包路径范围不符。')
            require(not item.is_dir() and not stat.S_ISLNK(item.external_attr >> 16), '压缩包包含目录/链接。')
            if name in expected:
                h = hashlib.sha256()
                with archive.open(item) as source:
                    for block in iter(lambda: source.read(1024 * 1024), b''):
                        h.update(block)
                require(h.hexdigest() == expected[name], '文件校验失败：' + name)
        total = sum(i.file_size for i in archive.infolist())
    return manifest, total


def command(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)


def require_root():
    require(sys.platform.startswith('linux') and os.geteuid() == 0, '请在Ubuntu服务器使用 sudo python3 运行。')


def service_text(kind):
    entry = {
        'web': '-m streamlit run streamlit_app.py --server.address=127.0.0.1 --server.port=8501 '
               '--server.headless=true --server.fileWatcherType=none --server.maxUploadSize=10 '
               '--browser.gatherUsageStats=false --client.showErrorDetails=none',
        'bot': 'feishu_bot.py', 'scheduler': 'run_scheduler.py'
    }[kind]
    return f'''[Unit]
Description=Parenting Agent {kind}
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=10

[Service]
Type=simple
User={ACCOUNT}
Group={ACCOUNT}
WorkingDirectory={APP}
Environment=APP_ENV=production
Environment=PARENTING_DATA_DIR={DATA}
Environment=HOME={DATA}
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=OMP_NUM_THREADS=1
Environment=OPENBLAS_NUM_THREADS=1
Environment=TZ=Asia/Shanghai
ExecStart={APP}/.venv/bin/python {entry}
Restart=on-failure
RestartSec=15
TimeoutStopSec=90
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths={DATA}

[Install]
WantedBy=multi-user.target
'''


PROBE = '''import asyncio, os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv('.env', encoding='utf-8-sig')
for key in ['DEEPSEEK_API_KEY','FEISHU_APP_ID','FEISHU_APP_SECRET','VISION_API_KEY','VISION_BASE_URL','VISION_MODEL']:
    assert os.getenv(key), key + ' missing'
assert len(os.getenv('WEB_PASSWORD','')) >= 16, 'WEB_PASSWORD too short'
asyncio.set_event_loop(asyncio.new_event_loop())
import streamlit, openai, lark_oapi
import feishu_bot
from storage import DATA_DIR
assert DATA_DIR == Path('/var/lib/parenting-agent'), 'wrong data directory'
from agent_v2.store import read_json
from family_features.records import browse_records
from family_features.media import resolve_photo
from family_features.settings import load_settings, allowed_push_chat
from family_features.tips import daily_tip
from datetime import date
settings = load_settings()
assert settings.chat_id and allowed_push_chat(settings.chat_id), 'push chat not allowed'
data = read_json(DATA_DIR / 'baby.json')
rows = browse_records(data)
assert data.get('profile'), 'missing profile'
for row in rows:
    for photo in row['record'].get('photos', []):
        assert resolve_photo(photo).is_file(), 'photo file missing'
daily_tip(date.today().isoformat())
print('SERVER_PREFLIGHT_OK | records=' + str(len(rows)))
'''


def runtime_env():
    env = os.environ.copy()
    # The installed .env is canonical; inherited sudo environment must not substitute keys.
    for key in list(env):
        if key.startswith(('DEEPSEEK_', 'VISION_', 'FEISHU_', 'STREAMLIT_')) or key == 'WEB_PASSWORD':
            env.pop(key, None)
    env.update(APP_ENV='production', PARENTING_DATA_DIR=str(DATA), HOME=str(DATA),
               PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
    return env


def preflight():
    result = subprocess.run(['runuser', '-u', ACCOUNT, '--', str(APP / '.venv/bin/python'), '-c', PROBE],
                            cwd=APP, env=runtime_env(), capture_output=True, text=True)
    if result.returncode:
        # No tracebacks containing private record payloads go into shared console logs.
        log = DATA / 'install-preflight.log'
        log.write_text(result.stdout + '\n' + result.stderr, encoding='utf-8')
        log.chmod(0o600)
        raise ValueError('服务器预检失败，服务尚未启动。详情保存在私有文件 ' + str(log)
                         + '；先告诉我“服务器预检失败”，不要上传完整日志。')
    print(result.stdout.strip())


def extract_payload(archive_path):
    with zipfile.ZipFile(archive_path) as archive:
        for item in archive.infolist():
            if item.filename == 'manifest.json':
                continue
            prefix, relative = item.filename.split('/', 1)
            target = (APP if prefix == 'app' else DATA) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(item) as source, target.open('wb') as dest:
                shutil.copyfileobj(source, dest)
            target.chmod(0o640 if prefix == 'app' else 0o600)


def install(archive_path):
    require_root()
    archive_path = Path(archive_path).resolve()
    require(archive_path.is_file(), '找不到迁移包。')
    os_release = Path('/etc/os-release').read_text()
    require('ID=ubuntu' in os_release and 'VERSION_ID="24.04"' in os_release,
            '此安装脚本针对Ubuntu 24.04，请先确认系统版本。')
    _, total = verify_archive(archive_path)
    package_hash = digest(archive_path)
    marker = APP / '.migration-package'
    ready = APP / '.deployment-ready'
    require(not ready.exists(), '已部署过，拒绝覆盖服务器数据。查看状态请使用 status。')
    if APP.exists() or DATA.exists():
        require(marker.is_file() and marker.read_text().strip() == package_hash,
                '目标目录已经存在且不是此包的未完成安装，拒绝覆盖。')
        for unit in SERVICES:
            require(subprocess.run(['systemctl', 'is-active', '--quiet', unit]).returncode != 0,
                    '已有育儿服务运行，拒绝重新导入。')
    else:
        for unit in SERVICES:
            require(not Path('/etc/systemd/system/' + unit + '.service').exists(), '已有同名服务，请先检查。')
        require(subprocess.run(['id', '-u', ACCOUNT], capture_output=True).returncode != 0,
                '已有同名系统账户，请先检查。')
    require(shutil.disk_usage('/opt').free > total * 2 + 2_000_000_000, '剩余磁盘不足。')
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', 8501))
        except OSError:
            raise ValueError('8501端口已被使用，停止安装。') from None
    print('校验通过。仅在独立目录安装育儿服务；不修改Nginx、现有网站或防火墙。', flush=True)
    os.umask(0o077)
    APP.mkdir(mode=0o750, exist_ok=True)
    DATA.mkdir(mode=0o700, exist_ok=True)
    marker.write_text(package_hash, encoding='ascii')
    extract_payload(archive_path)
    # Normalize BOM for all existing load_dotenv calls without reserializing secrets.
    env_path = APP / '.env'
    env_path.write_text(env_path.read_text(encoding='utf-8-sig'), encoding='utf-8')
    setup_env = dict(os.environ, DEBIAN_FRONTEND='noninteractive', NEEDRESTART_MODE='l')
    command(['apt-get', 'update'], env=setup_env)
    command(['apt-get', 'install', '-y', '--no-install-recommends', 'python3-venv', 'ca-certificates'], env=setup_env)
    if subprocess.run(['id', '-u', ACCOUNT], capture_output=True).returncode != 0:
        command(['useradd', '--system', '--user-group', '--home-dir', str(DATA), '--shell', '/usr/sbin/nologin', ACCOUNT])
    command(['python3', '-m', 'venv', APP / '.venv'])
    command([APP / '.venv/bin/python', '-m', 'pip', 'install', '--no-cache-dir', '--only-binary=:all:',
             '--timeout', '120', '--retries', '3', '-r', APP / 'requirements.txt'])
    command(['chown', '-R', 'root:' + ACCOUNT, APP])
    command(['chmod', '-R', 'g+rX,o-rwx', APP])
    command(['chown', '-R', ACCOUNT + ':' + ACCOUNT, DATA])
    command(['chmod', '-R', 'u+rwX,go-rwx', DATA])
    command(['chmod', '750', APP])
    preflight()
    for kind in ['web', 'bot', 'scheduler']:
        path = Path('/etc/systemd/system/parenting-' + kind + '.service')
        path.write_text(service_text(kind), encoding='utf-8')
        path.chmod(0o644)
    command(['systemd-analyze', 'verify', *['/etc/systemd/system/' + n + '.service' for n in SERVICES]])
    ready.write_text(package_hash, encoding='ascii')
    command(['systemctl', 'daemon-reload'])
    command(['systemctl', 'enable', '--now', *SERVICES])
    # Only web health is checked here; live Feishu/API acceptance still needs the user.
    for _ in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=2) as response:
                if response.status == 200:
                    break
        except OSError:
            time.sleep(1)
    status()
    print('已完成安装步骤。还需用飞书新消息和网页核对实际可用性。')
    print('迁移包仍保留，待验收后自行删除服务器上的ZIP；本机可留作私有备份。')


def status():
    require_root()
    failed = False
    for unit in SERVICES:
        result = subprocess.run(['systemctl', 'show', unit, '--property=ActiveState,SubState,UnitFileState,MemoryCurrent'],
                                capture_output=True, text=True)
        values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        print(unit + ': ' + ', '.join(k + '=' + v for k, v in values.items()))
        failed |= values.get('ActiveState') != 'active'
    try:
        with urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=5) as response:
            ok = response.status == 200
            print('Web health: ' + ('OK' if ok else 'FAILED'))
            failed |= not ok
    except OSError:
        print('Web health: NOT READY')
        failed = True
    if failed:
        raise ValueError('有服务未就绪，请把上述状态发来排查。')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    packing = modes.add_parser('pack')
    packing.add_argument('--project', default='.')
    packing.add_argument('--output')
    packing.add_argument('--stopped', action='store_true')
    installing = modes.add_parser('install')
    installing.add_argument('archive')
    modes.add_parser('status')
    args = parser.parse_args()
    try:
        if args.mode == 'pack':
            pack(args.project, args.output, args.stopped)
        elif args.mode == 'install':
            install(args.archive)
        else:
            status()
    except (ValueError, OSError, zipfile.BadZipFile) as exc:
        print('停止：' + str(exc), file=sys.stderr)
        return 1
    except subprocess.CalledProcessError:
        print('安装命令失败，请保留上方错误。未完成安装可用同一个包重试；不要删除数据目录。', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
