#!/usr/bin/env python3
"""SQLite-backed testcase vault for ARM64 SDC fuzzing."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(value: Optional[Dict[str, Any]]) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


@dataclass
class VaultEntry:
    testcase_key: str
    asm_content: str
    target_name: str
    policy_name: str = "sdc_fuzzing"
    ace_score: float = 0.0
    ibr_score: float = 0.0
    memory_pressure_score: float = 0.0
    risk_score: float = 0.0
    qemu_golden_hash: Optional[str] = None
    gem5_fault_hash: Optional[str] = None
    mcpat_power: Optional[float] = None
    status: str = "PENDING"
    metadata: Optional[Dict[str, Any]] = None

    def to_record(self) -> Dict[str, Any]:
        record = asdict(self)
        record["metadata_json"] = _json_dumps(record.pop("metadata"))
        return record


class SDCVault:
    """Persistent testcase storage for the offline/online SDC loop."""

    DEFAULT_SCHEMA_VERSION = 1

    def __init__(self, db_path: Path | str):
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._initialize()

    @property
    def path(self) -> Path:
        return self._db_path

    def close(self) -> None:
        self._conn.close()

    def _initialize(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vault_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS offline_testcases (
                    test_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    testcase_key TEXT NOT NULL UNIQUE,
                    target_name TEXT NOT NULL,
                    policy_name TEXT NOT NULL,
                    asm_content TEXT NOT NULL,
                    ace_score REAL NOT NULL DEFAULT 0.0,
                    ibr_score REAL NOT NULL DEFAULT 0.0,
                    memory_pressure_score REAL NOT NULL DEFAULT 0.0,
                    risk_score REAL NOT NULL DEFAULT 0.0,
                    qemu_golden_hash TEXT,
                    gem5_fault_hash TEXT,
                    mcpat_power REAL,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            self._conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_offline_testcases_status_risk
                ON offline_testcases(status, risk_score DESC, ace_score DESC, ibr_score DESC)
                """
            )
            self._conn.execute(
                """
                INSERT OR IGNORE INTO vault_meta(key, value)
                VALUES ('schema_version', ?)
                """,
                (str(self.DEFAULT_SCHEMA_VERSION),),
            )

    def upsert_testcase(self, entry: VaultEntry) -> int:
        now = _utcnow()
        record = entry.to_record()
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO offline_testcases (
                    testcase_key,
                    target_name,
                    policy_name,
                    asm_content,
                    ace_score,
                    ibr_score,
                    memory_pressure_score,
                    risk_score,
                    qemu_golden_hash,
                    gem5_fault_hash,
                    mcpat_power,
                    status,
                    metadata_json,
                    created_at,
                    updated_at
                ) VALUES (
                    :testcase_key,
                    :target_name,
                    :policy_name,
                    :asm_content,
                    :ace_score,
                    :ibr_score,
                    :memory_pressure_score,
                    :risk_score,
                    :qemu_golden_hash,
                    :gem5_fault_hash,
                    :mcpat_power,
                    :status,
                    :metadata_json,
                    :created_at,
                    :updated_at
                )
                ON CONFLICT(testcase_key) DO UPDATE SET
                    target_name=excluded.target_name,
                    policy_name=excluded.policy_name,
                    asm_content=excluded.asm_content,
                    ace_score=excluded.ace_score,
                    ibr_score=excluded.ibr_score,
                    memory_pressure_score=excluded.memory_pressure_score,
                    risk_score=excluded.risk_score,
                    qemu_golden_hash=COALESCE(excluded.qemu_golden_hash, offline_testcases.qemu_golden_hash),
                    gem5_fault_hash=COALESCE(excluded.gem5_fault_hash, offline_testcases.gem5_fault_hash),
                    mcpat_power=COALESCE(excluded.mcpat_power, offline_testcases.mcpat_power),
                    status=excluded.status,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                {
                    **record,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            row = self._conn.execute(
                "SELECT test_id FROM offline_testcases WHERE testcase_key = ?",
                (entry.testcase_key,),
            ).fetchone()
        assert row is not None
        return int(row["test_id"])

    def update_execution_result(
        self,
        testcase_key: str,
        *,
        qemu_golden_hash: Optional[str] = None,
        gem5_fault_hash: Optional[str] = None,
        mcpat_power: Optional[float] = None,
        status: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        assignments: List[str] = ["updated_at = :updated_at"]
        params: Dict[str, Any] = {"testcase_key": testcase_key, "updated_at": _utcnow()}

        if qemu_golden_hash is not None:
            assignments.append("qemu_golden_hash = :qemu_golden_hash")
            params["qemu_golden_hash"] = qemu_golden_hash
        if gem5_fault_hash is not None:
            assignments.append("gem5_fault_hash = :gem5_fault_hash")
            params["gem5_fault_hash"] = gem5_fault_hash
        if mcpat_power is not None:
            assignments.append("mcpat_power = :mcpat_power")
            params["mcpat_power"] = mcpat_power
        if status is not None:
            assignments.append("status = :status")
            params["status"] = status
        if metadata is not None:
            assignments.append("metadata_json = :metadata_json")
            params["metadata_json"] = _json_dumps(metadata)

        with self._conn:
            self._conn.execute(
                f"""
                UPDATE offline_testcases
                SET {", ".join(assignments)}
                WHERE testcase_key = :testcase_key
                """,
                params,
            )

    def mark_status(self, testcase_key: str, status: str) -> None:
        self.update_execution_result(testcase_key, status=status)

    def fetch_top_k_risky(
        self,
        limit: int,
        statuses: Sequence[str] = ("PENDING",),
    ) -> List[sqlite3.Row]:
        placeholders = ", ".join("?" for _ in statuses)
        query = f"""
            SELECT *
            FROM offline_testcases
            WHERE status IN ({placeholders})
            ORDER BY
                risk_score DESC,
                (ace_score * 0.6 + ibr_score * 0.4) DESC,
                memory_pressure_score DESC,
                test_id ASC
            LIMIT ?
        """
        cursor = self._conn.execute(query, [*statuses, limit])
        return cursor.fetchall()

    def list_testcases(
        self,
        *,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> List[sqlite3.Row]:
        if status is None:
            cursor = self._conn.execute(
                """
                SELECT *
                FROM offline_testcases
                ORDER BY test_id DESC
                LIMIT ?
                """,
                (limit,),
            )
        else:
            cursor = self._conn.execute(
                """
                SELECT *
                FROM offline_testcases
                WHERE status = ?
                ORDER BY test_id DESC
                LIMIT ?
                """,
                (status, limit),
            )
        return cursor.fetchall()

    def get_testcase(self, testcase_key: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM offline_testcases WHERE testcase_key = ?",
            (testcase_key,),
        ).fetchone()

    def count(self, *, status: Optional[str] = None) -> int:
        if status is None:
            row = self._conn.execute(
                "SELECT COUNT(*) AS count FROM offline_testcases"
            ).fetchone()
        else:
            row = self._conn.execute(
                "SELECT COUNT(*) AS count FROM offline_testcases WHERE status = ?",
                (status,),
            ).fetchone()
        assert row is not None
        return int(row["count"])

    def __enter__(self) -> "SDCVault":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

