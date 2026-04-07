#!/usr/bin/env python3
"""
MoltBook Collection Agent - Scheduler
Manages cron-based scheduled collection runs.
"""
import os
import sys
import json
import uuid
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
from config import CRON_DIR, BASE_DIR

logger = logging.getLogger(__name__)


class CollectionScheduler:
    """
    Manages cron schedules for the MoltBook Collection Agent.
    
    Each schedule is stored as a JSON file in CRON_DIR.
    The actual cron entry calls scheduler.py with the schedule ID.
    """

    def __init__(self):
        self.cron_dir = Path(CRON_DIR)
        self.cron_dir.mkdir(exist_ok=True)
        self.agent_path = BASE_DIR / "agent.py"

    # ───────────────────────────────────────────────────────────
    # Schedule management
    # ───────────────────────────────────────────────────────────

    def install_cron(self, schedule: str, collection_type: str = "all") -> str:
        """
        Install a cron schedule.
        
        Args:
            schedule: Cron expression (e.g., "0 9 * * *")
            collection_type: What to collect ("all", "posts", "enrich")
            
        Returns:
            Schedule ID (filename without .json)
        """
        schedule_id = f"cron-{uuid.uuid4().hex[:8]}"
        
        # Build schedule metadata
        meta = {
            "id": schedule_id,
            "cron": schedule,
            "collection_type": collection_type,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "last_run": None,
            "enabled": True,
        }

        # Save metadata
        meta_path = self.cron_dir / f"{schedule_id}.json"
        with open(meta_path, "w") as f:
            json.dump(meta, f, indent=2)

        # Install system cron entry
        self._install_system_cron(schedule_id, collection_type)

        logger.info(f"Installed cron schedule {schedule_id}: {schedule} ({collection_type})")
        return schedule_id

    def _install_system_cron(self, schedule_id: str, collection_type: str):
        """Add a crontab entry that runs agent.py with --schedule-id."""
        cron_line = (
            f'{schedule} cd {self.agent_path.parent} && '
            f'python3 {self.agent_path} run --mode {collection_type} --schedule-id {schedule_id} '
            f'>> {BASE_DIR}/logs/{schedule_id}.log 2>&1\n'
        )

        # Read existing crontab
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True,
        )
        existing = result.stdout if result.returncode == 0 else ""

        # Remove any existing entry for this schedule_id
        lines = [l for l in existing.splitlines() if schedule_id not in l]
        lines.append(cron_line.strip())

        # Write new crontab
        new_crontab = "\n".join(lines) + "\n"
        proc = subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            capture_output=True, text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to install crontab: {proc.stderr}")

    def list_schedules(self) -> List[Dict[str, Any]]:
        """List all installed schedules."""
        schedules = []
        for f in sorted(self.cron_dir.glob("*.json")):
            try:
                with open(f) as fh:
                    schedules.append(json.load(fh))
            except Exception as e:
                logger.warning(f"Could not read {f}: {e}")
        return schedules

    def remove_schedule(self, schedule_id: str) -> bool:
        """
        Remove a cron schedule by ID.
        
        Args:
            schedule_id: The schedule ID to remove
            
        Returns:
            True if removed, False if not found
        """
        meta_path = self.cron_dir / f"{schedule_id}.json"
        if not meta_path.exists():
            logger.warning(f"Schedule {schedule_id} not found")
            return False

        # Remove from system crontab
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            lines = [l for l in result.stdout.splitlines() if schedule_id not in l]
            new_crontab = "\n".join(lines) + "\n"
            subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True)

        # Remove metadata file
        meta_path.unlink()
        logger.info(f"Removed schedule {schedule_id}")
        return True

    def update_last_run(self, schedule_id: str):
        """Update last_run timestamp for a schedule."""
        meta_path = self.cron_dir / f"{schedule_id}.json"
        if meta_path.exists():
            with open(meta_path) as f:
                meta = json.load(f)
            meta["last_run"] = datetime.utcnow().isoformat() + "Z"
            with open(meta_path, "w") as f:
                json.dump(meta, f, indent=2)

    # ───────────────────────────────────────────────────────────
    # CLI interface
    # ───────────────────────────────────────────────────────────

    def cli(self, argv: List[str]):
        """Command-line interface for scheduler."""
        import argparse
        parser = argparse.ArgumentParser(description="MoltBook Collection Scheduler")
        sub = parser.add_subparsers(dest="command")

        install_p = sub.add_parser("install", help="Install a cron schedule")
        install_p.add_argument("cron", help="Cron expression (e.g., '0 9 * * *')")
        install_p.add_argument("type", nargs="?", default="all",
                                choices=["all", "posts", "enrich"],
                                help="Collection type")

        sub.add_parser("list", help="List all schedules")
        remove_p = sub.add_parser("remove", help="Remove a schedule")
        remove_p.add_argument("id", help="Schedule ID")

        args = parser.parse_args(argv)

        if args.command == "install":
            sid = self.install_cron(args.cron, args.type)
            print(f"Installed schedule: {sid}")
            print(f"Cron: {args.cron}")
            print(f"Collection type: {args.type}")

        elif args.command == "list":
            schedules = self.list_schedules()
            if not schedules:
                print("No schedules installed.")
                return
            for s in schedules:
                print(f"  {s['id']} | {s['cron']} | {s['collection_type']} | last_run: {s.get('last_run') or 'never'}")

        elif args.command == "remove":
            if self.remove_schedule(args.id):
                print(f"Removed schedule: {args.id}")
            else:
                print(f"Schedule not found: {args.id}")

        else:
            parser.print_help()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    scheduler = CollectionScheduler()
    scheduler.cli(sys.argv[1:])