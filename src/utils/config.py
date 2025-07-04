from dynaconf import Dynaconf
from utils.io_manager import get_env

env = get_env("APP_PROFILE")

config = Dynaconf(
    settings_files=[
        "resources/config.yaml",
        f"resources/config.{env}.yaml"
    ]
)

if __name__ == "__main__":
    print(env, config.app)