"""
Service layer for handling application settings.

This module provides the `SettingsService` class, which is responsible for
loading and saving application settings. Currently, it uses a JSON file
(`settings.json`) for persistence. This system is considered part of an older
configuration mechanism and might be subject to future refactoring or removal
in favor of more robust configuration management (e.g., environment variables
for all settings or a database-backed solution).
"""
import json
import os
import logging 
from typing import Dict, Any # For type hinting

# Create a logger instance for this module
logger = logging.getLogger(__name__)

class SettingsService:
    """
    A service class for managing application settings via a JSON file.

    This class provides static methods to load settings from and save settings
    to a predefined JSON file (`settings.json`). It is part of the older
    settings system.

    Attributes:
        SETTINGS_FILE (str): The name of the JSON file used for storing settings.
    """
    SETTINGS_FILE: str = 'settings.json'

    @staticmethod
    def load_settings() -> Dict[str, Any]:
        """
        Load settings from the JSON file specified by `SETTINGS_FILE`.

        If the file does not exist, is empty, or contains malformed JSON,
        an empty dictionary is returned and appropriate error/warning is logged.
        
        Returns:
            A dictionary containing the loaded settings.
        """
        logger.debug(f"Attempting to load settings from {SettingsService.SETTINGS_FILE}")
        if not os.path.exists(SettingsService.SETTINGS_FILE):
            logger.warning(f"Configuration file '{SettingsService.SETTINGS_FILE}' not found. Returning empty settings.")
            return {}
        try:
            with open(SettingsService.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings: Dict[str, Any] = json.load(f)
                logger.debug(f"Successfully loaded settings from {SettingsService.SETTINGS_FILE}")
                return settings
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from '{SettingsService.SETTINGS_FILE}': {e}. Returning empty settings.", exc_info=True)
            return {}
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading settings from '{SettingsService.SETTINGS_FILE}': {e}. Returning empty settings.", exc_info=True)
            return {}

    @staticmethod
    def save_settings(settings_data: Dict[str, Any]) -> None:
        """
        Save the provided settings data to the JSON file specified by `SETTINGS_FILE`.

        The data is saved in a human-readable format with an indent of 4 spaces.
        Logs success or failure of the operation.

        Args:
            settings_data: A dictionary containing the settings to be saved.
        """
        logger.debug(f"Attempting to save settings to {SettingsService.SETTINGS_FILE}")
        try:
            with open(SettingsService.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, indent=4, ensure_ascii=False)
            logger.info(f"Settings saved successfully to '{SettingsService.SETTINGS_FILE}'.")
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving settings to '{SettingsService.SETTINGS_FILE}': {e}.", exc_info=True)
