"""轻量数据库升级脚本（DATA-005）。

不做完整迁移框架（Alembic），只解决本项目真实会遇到的问题：
**给已有库补上后加的列**。SQLite 的 `ALTER TABLE ADD COLUMN` 足以覆盖新增字段场景；
删列/改列类型这类破坏性变更不在本脚本职责内，需要人工处理。

用法：
    cd backend
    python scripts/upgrade_db.py            # 预览将要执行的变更（dry-run）
    python scripts/upgrade_db.py --apply    # 真正执行

退出码：0 成功；1 执行出错。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 保证可以直接 `python scripts/upgrade_db.py` 运行
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, inspect, text  # noqa: E402

from app.config import settings  # noqa: E402
from app.db.database import Base  # noqa: E402
from app.db import models  # noqa: F401,E402  确保全部模型已注册到 Base

# 应用主引擎是 aiosqlite（异步），而 DDL 与元数据比对用同步连接更直接，
# 这里另开一个同步 engine 指向同一个库文件。
sync_engine = create_engine(f"sqlite:///{settings.db_path}")


def _sqlite_col_ddl(column) -> str | None:
    """生成 SQLite 的 ADD COLUMN 片段。

    SQLite 的 ADD COLUMN 限制：
    - 不能有 PRIMARY KEY / UNIQUE
    - NOT NULL 必须带默认值
    遇到无法满足的列直接跳过（返回 None），避免脚本把库搞坏。
    """
    if column.primary_key:
        return None
    if column.unique:
        return None
    type_sql = column.type.compile(sync_engine.dialect)
    parts = [f"{column.name} {type_sql}"]
    if not column.nullable:
        if column.default is not None or column.server_default is not None:
            parts.append("NOT NULL")
        else:
            # 无默认值的 NOT NULL 列，SQLite 不允许追加，跳过并提示
            return None
    return " ".join(parts)


def plan() -> list[str]:
    """对比模型定义与实际库结构，返回待执行的 DDL 列表。"""
    statements: list[str] = []
    insp = inspect(sync_engine)
    existing_tables = set(insp.get_table_names())
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        actual = {c["name"] for c in insp.get_columns(table.name)}
        for column in table.columns:
            if column.name in actual:
                continue
            ddl = _sqlite_col_ddl(column)
            if ddl is None:
                print(f"[跳过] {table.name}.{column.name}：SQLite 不支持追加该类型列，需人工处理")
                continue
            statements.append(f"ALTER TABLE {table.name} ADD COLUMN {ddl}")
    return statements


def main() -> int:
    parser = argparse.ArgumentParser(description="数据库结构升级（补齐新增列）")
    parser.add_argument("--apply", action="store_true", help="真正执行变更，默认只预览")
    args = parser.parse_args()

    print(f"数据库：{settings.db_path}")
    if not settings.db_path.exists():
        print("数据库文件不存在，请先启动一次服务以初始化。")
        return 1

    statements = plan()
    if not statements:
        print("库结构已是最新，无需升级。")
        return 0

    print(f"待执行 {len(statements)} 条变更：")
    for s in statements:
        print("  " + s)

    if not args.apply:
        print("\n这是预览模式（dry-run），加 --apply 才会真正执行。")
        return 0

    with sync_engine.begin() as conn:
        for s in statements:
            conn.execute(text(s))
    print("升级完成。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
