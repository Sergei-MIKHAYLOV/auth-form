from pathlib import Path
from dataclasses import dataclass
import logging
from environs import Env


env = Env()


@dataclass
class DatabaseSettings:
    db_name: str
    host: str
    port: int
    user: str
    password: str
    test_mode: bool

    @property
    def _current_db_name(self) -> str:
        if self.test_mode:
            return env.str('DB_NAME_TEST', default=self.db_name + '_test')
        return self.db_name
        

    @property
    def sync_url(self) -> str:
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self._current_db_name}"
    
    @property
    def async_url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self._current_db_name}"


@dataclass
class LogSettings:
    level: str
    format: str

@dataclass
class Config:
    db: DatabaseSettings
    log: LogSettings


def load_config(config_path: str | None = None,
                test_mode: bool = False) -> Config:

    if config_path:
        if not Path(config_path).exists():
            print(f'!!! .env file not found at {config_path}. Loading defaults.')
        else:
            print(f'Loading .env from {config_path}')

    env.read_env(path=config_path)

    db = DatabaseSettings(
        db_name=env.str('DB_NAME'),
        host=env.str('DB_HOST'),
        port=env.int('DB_PORT'),
        user=env.str('DB_USER'),
        password=env.str('DB_PASSWORD'),
        test_mode=env.bool('TEST_MODE', default=test_mode)
    )

    log = LogSettings(
        level=env.str('LOG_LEVEL', default='INFO'),
        format=env.str('LOG_FORMAT', 
                       default='[%(asctime)s] #%(levelname)-8s %(filename)s - %(message)s'),
    )

    logging.basicConfig(level=log.level, format=log.format)
    logger = logging.getLogger(__name__)
    logger.info('Configuration loaded successfully')

    return Config(db=db, log=log)
