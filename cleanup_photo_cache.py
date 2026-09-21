"""Optional cleanup of unreferenced new-format photos older than seven days."""
import argparse
import re
import time

from agent_v2.store import file_lock, read_json
from family_features.media import resolve_photo
from storage import data_path


def collect_paths(value, found):
    if isinstance(value, dict):
        for key, item in value.items():
            if key == 'photos' and isinstance(item, list):
                for photo in item:
                    try:
                        found.add(resolve_photo(photo))
                    except ValueError:
                        pass
            else:
                collect_paths(item, found)
    elif isinstance(value, list):
        for item in value:
            collect_paths(item, found)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    source=data_path('baby.json')
    if not source.exists():
        raise SystemExit('没有档案文件，无法确认引用关系，不执行清理。')
    with file_lock(source):
        data=read_json(source)
        referenced=set()
        collect_paths(data,referenced)
        candidates=[]
        for path in data_path('uploads').glob('*'):
            if path.is_file() and re.fullmatch(r'[0-9a-f]{32}\.(jpg|png|webp)',path.name):
                if path.resolve() not in referenced and time.time()-path.stat().st_mtime > 7*86400:
                    candidates.append(path)
        print(f'可清理未引用且超过7天的临时照片：{len(candidates)}张')
        if args.apply:
            for path in candidates:
                path.unlink()
            print('清理完成。档案、待确认操作和审计历史引用的照片均保留。')
        else:
            print('仅预览；加--apply才删除。不会清理旧版照片子目录。')


if __name__=='__main__':
    main()
