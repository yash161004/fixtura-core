import sqlite3
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from tools.base_tool import BaseTool

class SqliteArguments(BaseModel):
    operation: str = Field(..., description="'read' or 'write'")
    query: str
    parameters: List[Any] = Field(default_factory=list)

class SqliteTool(BaseTool):
    name = "sqlite_tool"
    is_idempotent = False
    is_reversible = False
    schema_cls = SqliteArguments
    
    def __init__(self, db_path: str):
        # DB file path is configurable and scoped; not passed via agent input.
        self.db_path = db_path
        
    def _run(self, args: SqliteArguments) -> Dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Use parameterized queries to neutralize SQL injection
            cursor.execute(args.query, args.parameters)
            
            if args.operation == "read":
                rows = cursor.fetchall()
                return {"rows": [dict(r) for r in rows]}
            elif args.operation == "write":
                conn.commit()
                return {"affected_rows": cursor.rowcount}
            else:
                raise ValueError(f"Unknown database operation: {args.operation}")
