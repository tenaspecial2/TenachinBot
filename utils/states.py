from aiogram.fsm.state import State, StatesGroup


class RegistrationState(StatesGroup):
    """States for user registration flow."""
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_role = State()


# Alias for backward compatibility
RegistrationStates = RegistrationState


class ConsultationStates(StatesGroup):
    """States for patient-doctor consultation."""
    waiting_for_symptoms = State()
    waiting_for_confirmation = State()


class FeedbackStates(StatesGroup):
    """States for submitting feedback."""
    waiting_for_feedback = State()


class PaymentStates(StatesGroup):
    """States for manual receipt submission."""
    waiting_for_receipt = State()