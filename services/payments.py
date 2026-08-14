from services.firebase import save_document, update_document, get_document


async def create_payment_record(payment_id: str, user_id: int, photo_id: str) -> None:
    """Create a new pending payment record in Firebase."""
    data = {
        "payment_id": payment_id,
        "user_id": user_id,
        "photo_id": photo_id,
        "status": "pending",
    }
    await save_document("payments", payment_id, data)


async def verify_payment(payment_id: str, user_id: int, status: str = "approved") -> None:
    """Approve or reject a payment."""
    await update_document("payments", payment_id, {"status": status})
    if status == "approved":
        await update_document("users", str(user_id), {"is_premium": True})