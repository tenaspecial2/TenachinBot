from services.firebase import get_document, update_document


async def check_user_membership(user_id: int) -> bool:
    """Check if a user has an active premium subscription."""
    user = await get_document("users", str(user_id))
    return user.get("is_premium", False) if user else False


async def grant_premium(user_id: int) -> None:
    """Grant premium status to a user."""
    await update_document("users", str(user_id), {"is_premium": True})


async def revoke_premium(user_id: int) -> None:
    """Revoke premium status from a user."""
    await update_document("users", str(user_id), {"is_premium": False})