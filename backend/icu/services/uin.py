from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from icu.models.uin_counter import UinCounter


async def allocate_next_uin(session: AsyncSession) -> int:
    """Gapless sequential UIN using locked single-row counter (variant B)."""
    row = await session.scalar(
        select(UinCounter).where(UinCounter.id == 1).with_for_update(),
    )
    if row is None:
        raise RuntimeError("uin_counter row missing; run migrations")
    row.value += 1
    new_uin = row.value
    await session.flush()
    return new_uin
