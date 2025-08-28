#!/bin/bash

# 独立队列Worker启动脚本（启用 gevent monkey patch）
# 用法：
#   chmod +x deploy/start_queue_worker.sh
#   ./deploy/start_queue_worker.sh

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

export QUEUE_WORKER=1

PYTHON=python3

RUNNER_FILE="queue_worker_runner.py"

cat > "$RUNNER_FILE" << 'PYEOF'
from gevent import monkey
monkey.patch_all()

import os
import time
import django
import threading

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zhiqing_server.settings")
django.setup()

from knowledge_mgt.api.upload_task_views import execute_query_with_params, process_upload_task

def fetch_one_pending_task():
    sql = """
        SELECT task_id FROM document_upload_task
        WHERE status = 'pending'
        ORDER BY created_at ASC
        LIMIT 1
    """
    rows = execute_query_with_params(sql, [])
    return rows[0]['task_id'] if rows else None

def main():
    print("[QueueWorker] started with gevent monkey.patch_all()")
    while True:
        try:
            task_id = fetch_one_pending_task()
            if task_id:
                # 串行处理，避免资源竞争。可按需改为协程并发小池。
                process_upload_task(task_id)
            else:
                time.sleep(1)
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"[QueueWorker] error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
PYEOF

$PYTHON "$RUNNER_FILE"


