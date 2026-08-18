from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SC-Link 供应链协同中台"
    secret_key: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str = "sclink_dev_root"
    db_name: str = "sc_link"

    admin_username: str = "admin"
    admin_password: str = "Admin@2026"

    max_login_attempts: int = 5
    lockout_minutes: int = 30

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_api_base: str = ""  # 留空用 Google 官方端点;中转服务时填其基地址
    ffmpeg_path: str = "ffmpeg"  # 视频验资抽帧;本地为独立静态版绝对路径,云服务器部署时按需配置


settings = Settings()
