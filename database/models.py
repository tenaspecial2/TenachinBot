from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class UserModel(BaseModel):
    telegram_id: int
    full_name: str
    phone_number: str
    username: Optional[str] = None
    role: str = "patient"  # patient, doctor, admin
    is_premium: bool = False
    is_banned: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConsultationModel(BaseModel):
    consultation_id: str
    patient_id: int
    doctor_id: Optional[int] = None
    status: str = "pending"  # pending, active, completed, cancelled
    symptoms: str
    medical_history: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PaymentModel(BaseModel):
    payment_id: str
    user_id: int
    amount: float
    status: str = "pending"  # pending, verified, rejected
    receipt_image_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HealthTipModel(BaseModel):
    tip_id: str
    title: str
    content: str
    category: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FeedbackModel(BaseModel):
    feedback_id: str
    user_id: int
    content: str
    rating: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)