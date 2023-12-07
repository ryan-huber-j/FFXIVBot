from dotenv import load_dotenv
import os
from bot import run_bot


if __name__ == "__main__":
    load_dotenv()
    run_bot(os.getenv('DISCORD_TOKEN'))