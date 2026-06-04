"""RQ worker entrypoint: python -m app.workers.worker"""

import sys

from redis import Redis
from rq import Worker

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.queue import QUEUE_NAME

logger = get_logger()


def main():
    settings = get_settings()
    configure_logging(settings.log_level)
    conn = Redis.from_url(settings.redis_url)
    queues = [QUEUE_NAME]
    worker = Worker(queues, connection=conn)
    logger.info("worker_starting", queues=queues)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    main()
    sys.exit(0)
