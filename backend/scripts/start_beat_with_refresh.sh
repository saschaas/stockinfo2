#!/bin/bash
set -e

echo "🚀 Starting Celery Beat with initial fund holdings refresh..."

# Give services a moment to fully initialize
# (docker-compose ensures Redis is healthy via depends_on)
echo "⏳ Waiting for services to stabilize..."
sleep 5
echo "✓ Services ready"

# Trigger immediate fund holdings check
echo "🔄 Triggering initial fund holdings check..."
python3 -c "
import sys
sys.path.insert(0, '/app')
from backend.app.tasks.funds import check_fund_holdings

try:
    task = check_fund_holdings.delay()
    print(f'✓ Fund holdings check queued (task ID: {task.id})')
except Exception as e:
    print(f'⚠️  Warning: Could not queue fund holdings check: {e}')
"

# Start Celery Beat
echo "📅 Starting Celery Beat scheduler..."
exec celery -A backend.app.celery_app beat --loglevel=info
