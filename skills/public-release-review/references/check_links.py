"""公開前の点検のための、Markdownのリンクの確認（public-release-review スキル）。

標準ライブラリだけで動く。WSL・Linuxでは python3、Windowsでは py -3 で実行する。
リポジトリの直下で実行する。

使い方:
  check_links.py internal   相対パスのリンクの先が実在するか（通信しない。先頭が / のリンクは
                            リポジトリの直下から、%20 などはデコードして解決する）
  check_links.py domains    外部リンクのドメインと件数の一覧（通信しない）
  check_links.py external   外部リンクにHEADを送り、失敗したものを出す（通信する）

オプション:
  --files A.md B.md ...     対象のMarkdown（既定: README.md と docs/*.md）
  --all                     external で、成功したものも出す
  --rewrite FILE            external で、確かめる前にURLを置き換える規則のファイル。
                            1行に「正規表現<TAB>置き換え後」を書く（# で始まる行は無視）。
                            例（ボット対策で取得できないサイトを、原稿のリポジトリで確かめる）:
                            ^https://docs\\.ros\\.org/en/jazzy/(?!p/)(.+)\\.html$<TAB>https://raw.githubusercontent.com/ros2/ros2_documentation/jazzy/source/\\1.rst
  --workers N               external の同時接続数（既定: 6）

拾うリンク: Markdownのリンク（題名付き [x](url "t") と、括弧を1段含むURLを含む）、
参照形式の定義（[x]: url）、HTMLの src="..." と href="..."。コードブロック（```）と
インラインのコード（`...`）の中は見ない。

GitHubの blob のリンク（https://github.com/<owner>/<repo>/blob/<ref>/<path>）は、
raw.githubusercontent.com の同じパスに置き換えて確かめる。
external は、各URLへHEADを送り、失敗したときだけGETで先頭1KBを取る。
User-Agentは偽装しない。送るのは要求だけで、ファイルやPCの情報は送らない。
"""

import argparse
import concurrent.futures
import pathlib
import re
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

LINK = re.compile(r'\]\((<[^>]+>|(?:[^()\s]|\([^()\s]*\))+)(?:\s+"[^"]*")?\)')
REF = re.compile(r'^\s*\[[^\]]+\]:\s*(\S+)')
HTML = re.compile(r'(?:src|href)="([^"]+)"')
CODE = re.compile(r'`[^`]*`')
BLOB = re.compile(r'^https://github\.com/([^/]+)/([^/]+)/blob/(.+)$')


# 対象のMarkdownのパスの一覧を返す。
def target_files(files):
    if files:
        return [pathlib.Path(f) for f in files]
    found = [pathlib.Path('README.md')] if pathlib.Path('README.md').exists() else []
    return found + sorted(pathlib.Path('docs').glob('*.md'))


# (ファイル, 行番号, リンク先) を順に返す。コードブロックとインラインのコードの中は見ない。
def links(files):
    for md in files:
        fenced = False
        for n, line in enumerate(md.read_text(encoding='utf-8').splitlines(), 1):
            if line.lstrip().startswith('```'):
                fenced = not fenced
                continue
            if fenced:
                continue
            text = CODE.sub('', line)
            for target in LINK.findall(text) + REF.findall(text) + HTML.findall(text):
                yield md, n, target.strip('<>')


# 相対パスのリンクの先が実在するかを確かめる。
def check_internal(files):
    bad = 0
    for md, n, target in links(files):
        if re.match(r'[a-z][a-z0-9+.-]*:', target) or target.startswith('#'):
            continue
        local = urllib.parse.unquote(target.split('#')[0].split('?')[0])
        base = pathlib.Path('.') if local.startswith('/') else md.parent
        path = (base / local.lstrip('/')).resolve()
        if not path.exists():
            bad += 1
            print(f'{md}:{n}: {target}')
    print(f'broken: {bad}')
    return bad


# 外部リンク（重複を除く）の一覧を返す。
def external_urls(files):
    return sorted({t for _, _, t in links(files) if re.match(r'https?://', t)})


# ドメインごとの件数を、多い順に出す。
def show_domains(files):
    counts = Counter(re.match(r'https?://([^/]+)', u).group(1) for u in external_urls(files))
    for domain, count in counts.most_common():
        print(f'{count:5d} {domain}')


# 置き換えの規則のファイルを読む。
def load_rewrites(path):
    rules = []
    if path:
        for line in pathlib.Path(path).read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.startswith('#'):
                pattern, repl = line.split('\t', 1)
                rules.append((re.compile(pattern), repl))
    return rules


# 確かめる先のURLを決める（フラグメントを外し、規則とGitHubのblobの置き換えを行う）。
def check_target(url, rules):
    target = url.split('#')[0]
    for pattern, repl in rules:
        if pattern.search(target):
            return pattern.sub(repl, target)
    m = BLOB.match(target)
    if m:
        return f'https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}'
    return target


# 1つのURLを確かめ、(結果, 元のURL, 確かめた先) を返す。
def probe(url, target):
    last = None
    for method, headers in (('HEAD', {}), ('GET', {'Range': 'bytes=0-1023'})):
        try:
            req = urllib.request.Request(target, method=method, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as res:
                return str(res.status), url, target
        except urllib.error.HTTPError as e:
            last = str(e.code)
        except urllib.error.URLError as e:
            last = 'DNS' if isinstance(e.reason, socket.gaierror) else f'ERR({e.reason})'
        except Exception as e:  # タイムアウトなど
            last = f'ERR({type(e).__name__})'
    return last, url, target


# 外部リンクを確かめ、失敗したもの（--all なら全件）を出す。
def check_external(files, rules, workers, show_all):
    urls = external_urls(files)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda u: probe(u, check_target(u, rules)), urls))
    ok = [r for r in results if r[0].startswith('2')]
    ng = [r for r in results if not r[0].startswith('2')]
    for code, url, target in sorted(results if show_all else ng):
        via = '' if url.split('#')[0] == target else f'  (checked: {target})'
        print(f'{code:>8} {url}{via}')
    print(f'total: {len(results)}, ok: {len(ok)}, failed: {len(ng)}')
    return len(ng)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['internal', 'domains', 'external'])
    parser.add_argument('--files', nargs='*')
    parser.add_argument('--all', action='store_true')
    parser.add_argument('--rewrite')
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    files = target_files(args.files)
    if args.command == 'internal':
        sys.exit(1 if check_internal(files) else 0)
    if args.command == 'domains':
        show_domains(files)
        return
    sys.exit(1 if check_external(files, load_rewrites(args.rewrite), args.workers, args.all) else 0)


if __name__ == '__main__':
    main()
