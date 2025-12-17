from sqlalchemy import Column
from typing import Dict, Any
import operator

OPS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "lt": operator.lt,
    "le": operator.le,
    "gt": operator.gt,
    "ge": operator.ge,
    "like": lambda col, val: col.like(val),
    "ilike": lambda col, val: col.ilike(val),
}

def parse_query_filters(query_params: Dict[str, str], table):
    filters = []
    for key, value in query_params.items():
        if key in ("skip", "limit"):
            continue
        if "__" in key:
            col_name, op_name = key.rsplit("__", 1)
            op = OPS.get(op_name, OPS["eq"])
        else:
            col_name, op = key, OPS["eq"]

        if col_name in table.c:
            col: Column = table.c[col_name]
            if col.type.python_type in (int, float, bool):
                try:
                    value = col.type.python_type(value)
                except (ValueError, TypeError):
                    continue
            filters.append(op(col, value))
    return filters