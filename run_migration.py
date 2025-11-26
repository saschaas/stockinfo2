import asyncio
from backend.app.db.session import async_session_factory
from sqlalchemy import text

async def run_migration():
    async with async_session_factory() as session:
        await session.execute(text('CREATE INDEX IF NOT EXISTS idx_stock_analyses_sector ON stock_analyses(sector)'))
        await session.execute(text('CREATE INDEX IF NOT EXISTS idx_stock_analyses_sector_date ON stock_analyses(sector, analysis_date DESC)'))
        await session.commit()
        print('✓ Database indexes created successfully')

if __name__ == '__main__':
    asyncio.run(run_migration())
