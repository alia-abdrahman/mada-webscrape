from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "mada"

    headless: bool = True
    log_level: str = "INFO"

    publicinfobanjir_url: str = "https://publicinfobanjir.water.gov.my"
    publicinfobanjir_json_path: str = "/wp-content/themes/enlighten/data/latestreadingstrendabc.json"
    met_cuaca_url: str = "https://www.met.gov.my"
    met_cuaca_json_path: str = "/json/cuaca_semasa/data.json"
    jupem_water_level_url: str = "https://jupem.gov.my"
    jupem_staps_path: str = "/ms/staps"

    flood_collection: str = "flood"
    weather_collection: str = "weather"
    water_level_collection: str = "water_level"

    default_timeout: int = Field(default=30, description="Selenium wait timeout, seconds")


settings = Settings()
