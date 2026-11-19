from email.message import EmailMessage

import aiosmtplib
from pydantic_settings import BaseSettings, SettingsConfigDict


class EmailSettings(BaseSettings):
    SMTP_HOST: str = "127.0.0.1"
    SMTP_PORT: int = 1025
    SMTP_FROM_EMAIL: str = "noreply@online-cinema.local"
    BASE_URL: str = "http://127.0.0.1:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = EmailSettings()


async def send_activation_email(
    recipient: str,
    token: str,
) -> None:
    activation_link = f"{settings.BASE_URL}/api/v1/accounts/activate/" f"?token={token}"

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = recipient
    message["Subject"] = "Activate your Online Cinema account"

    message.set_content(
        "Welcome to Online Cinema!\n\n"
        "To activate your account, follow this link:\n"
        f"{activation_link}\n\n"
        "This link is valid for 24 hours."
    )

    await aiosmtplib.send(
        message,
        hostname=settings.SMTP_HOST,
        port=settings.SMTP_PORT,
        start_tls=False,
        use_tls=False,
    )
