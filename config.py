import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8011864164:AAG5Xxst4OiMPZtXncH-c1wJA6Fz15Xr5Pc")
    WEBHOOK_URL: str | None = os.getenv("WEBHOOK_URL", None)
    
    # Admin ID
    ADMIN_IDS: list[int] = field(default_factory=lambda: [501384766])
    
    # Default Specialist ID
    DEFAULT_SPECIALIST_ID: int = 5872954068
    
    # Specialists Registry (Name -> Telegram ID)
    SPECIALISTS: dict[str, int] = field(default_factory=lambda: {
        "Abebe": 5872954068,
        "Kebede": 8571717581,
    })

    def get_specialist_id(self, name: str) -> int:
        """Returns the Telegram ID for a named specialist, defaulting to Abebe."""
        return self.SPECIALISTS.get(name, self.DEFAULT_SPECIALIST_ID)


settings = Settings()