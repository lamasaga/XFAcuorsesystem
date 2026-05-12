"""
========================================
数据库兼容层
========================================

提供 PortableArray 自定义列类型，
在 PostgreSQL 下使用原生 ARRAY，在 SQLite 下使用 JSON 存储列表。

使用方法：
    from app.core.compat import PortableArray, StringArray, IntArray

    # 替代 ARRAY(String)
    column = Column(StringArray, default=[])

    # 替代 ARRAY(Integer)
    column = Column(IntArray, default=[])
"""

import json
import os
from sqlalchemy import TypeDecorator, Text, JSON
from sqlalchemy.types import TypeEngine

# 判断是否使用 SQLite（通过环境变量）
_USE_SQLITE = os.getenv("USE_SQLITE", "false").lower() == "true"


class PortableArray(TypeDecorator):
    """
    跨数据库兼容的数组类型。

    - PostgreSQL: 使用原生 ARRAY 类型
    - SQLite: 使用 JSON 文本存储
    """
    impl = Text
    cache_ok = True

    def __init__(self, item_type=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.item_type = item_type

    def load_dialect_impl(self, dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import ARRAY
            from sqlalchemy import String, Integer
            if self.item_type == "integer":
                return dialect.type_descriptor(ARRAY(Integer))
            return dialect.type_descriptor(ARRAY(String))
        else:
            return dialect.type_descriptor(Text())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        # SQLite: 序列化为 JSON 字符串
        return json.dumps(value, ensure_ascii=False)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        if dialect.name == "postgresql":
            return value if value else []
        # SQLite: 从 JSON 字符串反序列化
        if isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        return value if isinstance(value, list) else []


# 便捷别名
StringArray = PortableArray(item_type="string")
IntArray = PortableArray(item_type="integer")


def is_sqlite_mode() -> bool:
    """判断当前是否为 SQLite 模式"""
    return _USE_SQLITE
