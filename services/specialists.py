from services.firebase import save_document, get_document


async def register_doctor(doctor_id: int, full_name: str, specialty: str) -> None:
    """Register or update a doctor profile."""
    data = {
        "doctor_id": doctor_id,
        "full_name": full_name,
        "specialty": specialty,
        "is_active": True,
    }
    await save_document("doctors", str(doctor_id), data)


async def get_doctor_profile(doctor_id: int) -> dict:
    """Fetch a doctor's details."""
    return await get_document("doctors", str(doctor_id))