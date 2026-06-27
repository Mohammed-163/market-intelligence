"""
file_manager.py
Read and write JSON, CSV, and plain text files safely.
"""
import json
import csv
from pathlib import Path
from typing import Any, List, Dict
from utils.logger import get_logger

logger = get_logger()


class FileManager:
    @staticmethod
    def ensure_dir(path: str):
        Path(path).parent.mkdir(parents=True, exist_ok=True)

    def read_json(self, path: str) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def write_json(self, path: str, data: Any, indent: int = 2) -> None:
        self.ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=indent)
        logger.debug(f"Written JSON: {path}")

    def read_csv(self, path: str) -> List[Dict]:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def write_csv(self, path: str, rows: List[Dict], fieldnames: List[str] = None) -> None:
        self.ensure_dir(path)
        if not rows:
            return
        fn = fieldnames or list(rows[0].keys())
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fn)
            writer.writeheader()
            writer.writerows(rows)
        logger.debug(f"Written CSV: {path}")

    def read_text(self, path: str) -> str:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def write_text(self, path: str, content: str) -> None:
        self.ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        logger.debug(f"Written text: {path}")
