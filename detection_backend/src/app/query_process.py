from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.orm.run_result import RedisResults  # import model của bạn

def stream_redisresults(session: Session, batch_size: int = 1000):
    offset = 0
    
    while True:
        stmt = (
            select(RedisResults)
            .order_by(RedisResults.id)
            .offset(offset)
            .limit(batch_size)
        )

        results = session.execute(stmt).scalars().all()

        if not results:
            break

        for row in results:
            yield row

        offset += batch_size
