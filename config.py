# env_config.py
from copy import deepcopy
from collections import namedtuple
from typing import Any, Dict, List
from dotenv import dotenv_values
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class Config:
    """
    Singleton-style class that loads .env once and exposes variables as a namedtuple.

    Usage:
        from env_config import env

        print(env.config.DATABASE_URL)
        print(env.config.SECRET_KEY)
    """

    _instance = None
    _env_tuple = None
    _env_dict: Dict[str, str] = {}
    _parsed_compliance_checks: List[Dict[str, Any]] = []
    _parsed_application_schema: List[Dict[str, Any]] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._load_env()
        return cls._instance

    @classmethod
    def _load_env(cls):
        """Load .env file once and create the namedtuple."""
        cls._env_dict = dotenv_values(".env")

        # Create namedtuple with dynamic fields
        field_names = list(cls._env_dict.keys())

        EnvTuple = namedtuple(
            typename="EnvConfigTuple",
            field_names=field_names,
            defaults=None,  # no defaults
            rename=False,  # raise on invalid names
        )

        cls._env_tuple = EnvTuple(**cls._env_dict)

    @property
    def config(self):
        """Return the frozen namedtuple of environment variables."""
        return self._env_tuple

    def get(self, key: str, default: Any = None) -> Any:
        """Safe get similar to dict.get()"""
        return getattr(self._env_tuple, key, default)

    def as_dict(self) -> Dict[str, str]:
        """Return a copy of the underlying dictionary."""
        return self._env_dict.copy()

    def reload(self):
        """Force reload of .env (useful during development)."""
        self._env_tuple = None
        self._env_dict = {}
        type(self)._load_env()

    def configured_compliance_checks(self):
        if len(self._parsed_compliance_checks) > 0:
            return deepcopy(self._parsed_compliance_checks)
        config_checks: List[Dict[str, Any]] = []
        try:
            config_checks = json.loads(self.get("VERIFICATION_CHECKS", "[]"))
            logger.info(
                f"Successfully loaded {len(config_checks)} dynamic verification rules from environment."
            )
        except Exception as e:
            logger.critical(
                f"Failed to parse VERIFICATION_CHECKS from environment. Check JSON formatting. Error: {e}"
            )

        if len(config_checks) > 0:
            self._parsed_compliance_checks = config_checks
        return deepcopy(config_checks)

    def configured_application_schema(self):
        if len(self._parsed_application_schema) > 0:
            return deepcopy(self._parsed_application_schema)
        application_schema: List[Dict[str, Any]] = []
        try:
            application_schema = json.loads(self.get("APPLICATION_SCHEMA", "[]"))
            logger.info(
                f"Successfully loaded {len(application_schema)} dynamic verification rules from environment."
            )
        except Exception as e:
            logger.critical(
                f"Failed to parse APPLICATION_SCHEMA from environment. Check JSON formatting. Error: {e}"
            )

        if len(application_schema) > 0:
            self._parsed_application_schema = application_schema
        return deepcopy(application_schema)


env = Config()


__all__ = ["env", "Config"]
