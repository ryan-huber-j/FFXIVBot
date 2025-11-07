import logging
import os

from dotenv import load_dotenv

from domain import Config

_config: Config = None


def load_config() -> Config:
    global _config
    if _config is not None:
        return _config

    load_dotenv()

    discord_token = os.getenv("DISCORD_TOKEN")
    discord_application_id = int(os.getenv("APPLICATION_ID"))
    discord_guild_id = int(os.getenv("GUILD_ID"))

    lodestone_url = os.getenv("LODESTONE_URL", "https://na.finalfantasyxiv.com")
    free_company_id = os.getenv("FREE_COMPANY_ID", "")
    world_name = os.getenv("WORLD_NAME", "Siren")
    data_center = os.getenv("DATA_CENTER", "Aether")

    # Create a logger that emits WARNING+ to stderr
    logger = logging.getLogger("ffxivbot")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setLevel(logging.WARNING)
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    _config = Config(
        discord_token=discord_token,
        discord_application_id=discord_application_id,
        discord_guild_id=discord_guild_id,
        lodestone_url=lodestone_url,
        free_company_id=free_company_id,
        data_center=data_center,
        world_name=world_name,
        logger=logger,
    )
    return _config
