import os
import sys
import logging
import redis
from rq import Worker, Connection
from app.core.config import settings
from app.core.logging_config import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def main():
    """Main worker function"""
    logger.info("Starting RQ Worker...")
    
    # Connect to Redis
    redis_conn = redis.Redis.from_url(settings.REDIS_URL)
    
    # Test Redis connection
    try:
        redis_conn.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        sys.exit(1)
    
    # Create worker
    with Connection(redis_conn):
        worker = Worker(['code_execution', 'default'])
        logger.info("Worker started, waiting for jobs...")
        worker.work()

if __name__ == '__main__':
    main()