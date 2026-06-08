"""
core/config.py
==============
إعدادات النظام المركزية — يتم تحميلها مرة واحدة عند بدء التشغيل.
يستخدم pydantic-settings لقراءة المتغيرات من ملف .env أو بيئة النظام.
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # ─── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite:///./neoshop.db"

    # ─── JWT ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ─── MQTT ─────────────────────────────────────────────────────────────
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""

    # ─── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENV: str = "development"
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ─── Admin ────────────────────────────────────────────────────────────
    ADMIN_EMAILS: str = "admin@neoshop.com,owner@neoshop.com"

    # ─── CV / YOLO ────────────────────────────────────────────────────────
    YOLO_MODEL_PATH: str = "yolov8n.pt"
    CAMERA_STREAM_URL: str = "0"

    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_allowed_origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    def get_admin_emails(self) -> List[str]:
        return [e.strip() for e in self.ADMIN_EMAILS.split(",")]


settings = Settings()
