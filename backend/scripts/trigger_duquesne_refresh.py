"""Trigger holdings refresh for Duquesne Family Office."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.app.tasks.funds import refresh_single_fund

# Trigger refresh for Duquesne (fund ID 23)
task = refresh_single_fund.delay(23)

print(f"Triggered holdings refresh for Duquesne Family Office")
print(f"Task ID: {task.id}")
