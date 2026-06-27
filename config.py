# env_config.py
import os
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
    # Runtime overrides: take precedence over .env values.
    # Note: class-level, so shared across the process.
    # Only changes settings for current interface.
    _overrides: Dict[str, str] = {}

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
        """Runtime overrides take precedence over .env values."""
        if key in self._overrides:
            return self._overrides[key]
        return getattr(self._env_tuple, key, default)

    def override(self, key: str, value: str | None):
        """
        Set or clear a runtime override for this session.
        Also writes to os.environ so engine code using os.getenv() picks it up.
        Pass None or empty string to clear the override and restore the .env default.
        """
        if value:
            self._overrides[key] = value
            os.environ[key] = value
        else:
            self._overrides.pop(key, None)
            original = self._env_dict.get(key)
            if original is not None:
                os.environ[key] = original
            elif key in os.environ:
                del os.environ[key]
        # Invalidate parsed caches for JSON schema keys so the next read re-parses.
        if key == "VERIFICATION_CHECKS":
            self._parsed_compliance_checks = []
        elif key == "APPLICATION_SCHEMA":
            self._parsed_application_schema = []

    def clear_overrides(self):
        """Remove all runtime overrides and restore .env values in os.environ."""
        for key in list(self._overrides.keys()):
            original = self._env_dict.get(key)
            if original is not None:
                os.environ[key] = original
            elif key in os.environ:
                del os.environ[key]
            if key == "VERIFICATION_CHECKS":
                self._parsed_compliance_checks = []
            elif key == "APPLICATION_SCHEMA":
                self._parsed_application_schema = []
        self._overrides.clear()

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

    def get_active_compliance_checks(self, beverage_category):
        return [
            c
            for c in env.configured_compliance_checks()
            if "ALL" in c.get("applicable_categories", ["ALL"])
            or beverage_category in c.get("applicable_categories", [])
        ]

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
