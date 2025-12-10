import asyncio
from sqlalchemy import select
from backend.app.db.session import async_session_factory
from backend.app.db.models import Fund, FundHolding

async def check_citadel():
    async with async_session_factory() as session:
        # Get Citadel fund
        result = await session.execute(
            select(Fund).where(Fund.name.like('%Citadel%'))
        )
        fund = result.scalar_one_or_none()

        if fund:
            print(f'Fund: {fund.name} (ID: {fund.id})')
            print(f'CIK: {fund.cik}')

            # Get holdings for latest filing date
            result = await session.execute(
                select(FundHolding.filing_date)
                .where(FundHolding.fund_id == fund.id)
                .distinct()
                .order_by(FundHolding.filing_date.desc())
                .limit(1)
            )
            latest_date = result.scalar_one_or_none()
            print(f'Latest filing date: {latest_date}')

            # Get holdings for that date
            result = await session.execute(
                select(FundHolding)
                .where(FundHolding.fund_id == fund.id)
                .where(FundHolding.filing_date == latest_date)
                .order_by(FundHolding.ticker)
            )
            holdings = result.scalars().all()

            print(f'\nTotal holdings for {latest_date}: {len(holdings)}')
            print('\nChecking for duplicates:')
            ticker_counts = {}
            for h in holdings:
                if h.ticker not in ticker_counts:
                    ticker_counts[h.ticker] = []
                ticker_counts[h.ticker].append(h)

            duplicates = {k: v for k, v in ticker_counts.items() if len(v) > 1}
            if duplicates:
                print(f'Found {len(duplicates)} duplicate tickers:')
                for ticker, holdings_list in list(duplicates.items())[:5]:
                    print(f'\n{ticker}:')
                    for h in holdings_list:
                        print(f'  ID: {h.id} | {h.company_name} | {h.shares} shares | ${h.value} | Filing: {h.filing_date}')
            else:
                print('No duplicates found!')

asyncio.run(check_citadel())
