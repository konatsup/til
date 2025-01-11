#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
update_readme.py

以下のことを行う:
1. リポジトリ直下にあるトピックフォルダ（python, rustなど）を取得
2. 各トピックフォルダ以下を再帰的に走査し、.mdファイルを拾う
3. ディレクトリ階層を反映したツリー状データを作る
4. ツリーをMarkdown形式に整形し、README.mdを生成 or 上書きする

依存ライブラリ: なし (標準ライブラリのみ)
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Union

# 除外フォルダ
IGNORE_DIRS = {'.git', '.github', 'scripts', '__pycache__', 'node_modules'}

# 除外ファイル名
IGNORE_FILES = {'README.md'}

# このスクリプトのあるディレクトリから見たルート
ROOT_DIR = Path(__file__).parent
README_PATH = ROOT_DIR / 'README.md'

def main():
    """
    エントリーポイント:
      1. トップレベルフォルダを走査して、トピックとみなす
      2. 各トピック以下を再帰的に探索
      3. Markdownを生成し、READMEを上書き
    """
    # 1. トップレベルディレクトリ (＝ トピック) を取得
    topic_dirs = []
    for item in ROOT_DIR.iterdir():
        if item.is_dir() and item.name not in IGNORE_DIRS:
            topic_dirs.append(item)

    topic_dirs.sort(key=lambda d: d.name.lower())

    # 2. 各トピックフォルダを再帰的に探索し、ツリーデータを構築
    #    構造例：
    #    {
    #      "python": {
    #         "__files__": [(title, "python/basics.md"), (title, "python/decorators.md")],
    #         "advanced": {
    #             "__files__": [(title, "python/advanced/metaprogramming.md"), ...]
    #         }
    #      },
    #      "rust": {
    #         "__files__": [(title, "rust/macros.md")]
    #      }
    #    }
    all_topics_data = {}
    for topic_dir in topic_dirs:
        tree = build_directory_tree(topic_dir)
        all_topics_data[topic_dir.name] = tree

    # 3. README.mdの本文を生成
    new_readme_content = generate_readme(all_topics_data)

    # 4. 実際にREADME.mdを書き換える
    with README_PATH.open('w', encoding='utf-8') as f:
        f.write(new_readme_content)

    print("[INFO] README.md updated!")


def build_directory_tree(current_dir: Path) -> dict:
    """
    再帰的にcurrent_dirを探索し、次のような構造の辞書を返す:
    {
      "__files__": [(title, relative_path), (title, relative_path), ...],
      "subdirA": {
        "__files__": [...],
        "subsubdirB": { ... },
        ...
      },
      ...
    }
    """
    tree = {"__files__": []}

    # カレントディレクトリ直下の要素を列挙
    for item in sorted(current_dir.iterdir(), key=lambda p: p.name.lower()):
        if item.is_dir():
            # 除外フォルダチェック
            if item.name in IGNORE_DIRS:
                continue
            # 再帰的にツリーを作成
            subtree = build_directory_tree(item)
            tree[item.name] = subtree
        else:
            # ファイルの場合
            if item.suffix == '.md' and item.name not in IGNORE_FILES:
                # タイトルを抽出
                title = extract_title_from_md(item)
                relative_path = item.relative_to(ROOT_DIR).as_posix()
                tree["__files__"].append((title, relative_path))

    return tree


def extract_title_from_md(md_file: Path) -> str:
    """
    mdファイルの先頭行からタイトル(# 見出し)を抽出。
    見つからなければファイル名(拡張子除く)を使う。
    """
    with md_file.open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#'):
                # "#", "##", "###" 等に対応するなら
                # 正規表現で `#` の数やスペースを取り除く
                return re.sub(r'^#+\s*', '', line).strip()
    return md_file.stem  # デフォルトはファイル名


def generate_readme(all_topics_data: Dict[str, dict]) -> str:
    """
    全トピック分のツリーから、README.md の全文を組み立てる。
    - all_topics_data: { "python": { "__files__": [...], "subdir": {...} }, "rust": ... }
    """

    # まずは「Categories」一覧を作る (トピック一覧のみ)
    categories_lines = []
    for topic_name in sorted(all_topics_data.keys(), key=str.lower):
        anchor = make_anchor(topic_name, level=2)
        categories_lines.append(f"- [{topic_name}](#{anchor})")

    # 次に Articles セクションを構築
    articles_lines = []
    for topic_name in sorted(all_topics_data.keys(), key=str.lower):
        articles_lines.append(f"### {topic_name}")
        topic_tree = all_topics_data[topic_name]

        # トピック配下を再帰的にMarkdown化する
        subtree_md = render_subtree(topic_tree, heading_level=4, parent_path=topic_name)
        articles_lines.append(subtree_md)

    return f"""# TIL (Today I Learned)

日々学習したことを簡単にまとめたリポジトリです。

あくまで個人的な学習メモであり、正確性を保証するものではありません。

※こちらのファイルは自動生成されており直接修正することは禁止です。

## Categories
{os.linesep.join(categories_lines)}

## Articles
{os.linesep.join(articles_lines)}
"""


def render_subtree(tree: dict, heading_level: int, parent_path: str) -> str:
    """
    ツリー(dict)をMarkdown文字列に再帰的に変換。
    - tree: { "__files__": [(title, path), ...], "subdir": {...}, ... }
    - heading_level: 見出しレベル (例: 3 -> "###")
    - parent_path: 見出しアンカー用に利用 (例: "python/advanced")
    """

    lines = []
    # 1. まず "__files__" のリストをリスト表示
    files = tree.get("__files__", [])
    if files:
        for (title, rel_path) in files:
            lines.append(f"- [{title}]({rel_path})")
        # ファイル一覧の後に空行を入れる
        lines.append("")

    # 2. 次にサブディレクトリをアルファベット順で処理
    subdirs = [k for k in tree.keys() if k != "__files__"]
    subdirs.sort(key=str.lower)

    for subdir in subdirs:
        subtree = tree[subdir]
        heading_prefix = "#" * heading_level  # 例: "###"
        # 見出しを出力 + 直後に空行を入れる
        lines.append(f"{heading_prefix} {subdir}")
        lines.append("")

        # 再帰呼び出し
        subtree_md = render_subtree(subtree, heading_level + 1, f"{parent_path}/{subdir}")
        lines.append(subtree_md)
        # サブディレクトリブロックの後に空行
        lines.append("")

    # 不要な連続改行を防ぐため、最後でjoinする前に整形
    # ただし「末尾に空行が増えすぎる」など気になる場合は調整
    return "\n".join(line for line in lines if line is not None)


def make_anchor(text: str, level: int = 2) -> str:
    """
    GitHub風のアンカー文字列を作る簡易関数
    例: "Advanced Topics" -> "advanced-topics"
    """
    # 実際のGitHubアンカーは細かいルールがあるが、ここではシンプルにしている
    anchor = re.sub(r'\s+', '-', text.lower())
    return anchor


if __name__ == '__main__':
    main()
