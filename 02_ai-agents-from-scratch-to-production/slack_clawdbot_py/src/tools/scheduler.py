import threading
import time
from typing import Optional, List
from datetime import datetime
try:
    from croniter import croniter
except ImportError:
    croniter = None
from ..memory.database import (
    create_scheduled_task,
    get_pending_tasks,
    update_task_status,
    ScheduledTask
)
from .slack_actions import send_message
from ..utils.logger import create_module_logger

logger = create_module_logger("scheduler")

class TaskScheduler:
    def __init__(self, check_interval_seconds: int = 30):
        self.check_interval = check_interval_seconds
        self.is_running = False
        self.timer: Optional[threading.Timer] = None

    def start(self) -> None:
        if self.is_running:
            return
        self.is_running = True
        logger.info("Task scheduler started")
        self._schedule_next_check()

    def stop(self) -> None:
        self.is_running = False
        if self.timer:
            self.timer.cancel()
            self.timer = None
        logger.info("Task scheduler stopped")

    def _schedule_next_check(self) -> None:
        if not self.is_running:
            return
        self.timer = threading.Timer(self.check_interval, self._check_and_execute_tasks)
        self.timer.daemon = True
        self.timer.start()

    def _check_and_execute_tasks(self) -> None:
        try:
            now = int(time.time())
            pending = get_pending_tasks()
            
            for task in pending:
                should_execute = False
                
                # Check one-time scheduled task
                if task.scheduled_time and task.scheduled_time <= now:
                    should_execute = True
                
                # Check recurring cron expression
                elif task.cron_expression:
                    try:
                        base_dt = datetime.fromtimestamp(task.created_at)
                        cron = croniter(task.cron_expression, base_dt)
                        next_run = cron.get_next()
                        if next_run <= now:
                            should_execute = True
                    except Exception as e:
                        logger.error(f"Error evaluating cron '{task.cron_expression}' for task {task.id}: {e}")

                if should_execute:
                    self._run_task(task)

        except Exception as e:
            logger.error(f"Error during scheduled task check: {e}")
        finally:
            self._schedule_next_check()

    def _run_task(self, task: ScheduledTask) -> None:
        logger.info(f"Executing scheduled task #{task.id}: '{task.task_description}' in {task.channel_id}")
        try:
            send_message(
                target=task.channel_id,
                message=task.task_description,
                thread_ts=task.thread_ts
            )
            # If not a recurring cron, mark as completed
            if not task.cron_expression:
                update_task_status(task.id, status="completed", executed_at=int(time.time()))
            else:
                # Update executed_at for cron task
                update_task_status(task.id, status="pending", executed_at=int(time.time()))
        except Exception as e:
            logger.error(f"Failed to execute task #{task.id}: {e}")
            update_task_status(task.id, status="failed", executed_at=int(time.time()))

    def schedule_task(
        self,
        user_id: str,
        channel_id: str,
        task_description: str,
        scheduled_time: Optional[int] = None,
        cron_expression: Optional[str] = None
    ) -> int:
        task_id = create_scheduled_task(
            user_id=user_id,
            channel_id=channel_id,
            task_description=task_description,
            scheduled_time=scheduled_time,
            cron_expression=cron_expression
        )
        logger.info(f"Scheduled new task #{task_id} for user {user_id}")
        return task_id

task_scheduler = TaskScheduler()
