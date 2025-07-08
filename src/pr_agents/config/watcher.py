"""
Configuration file watcher for hot-reloading.
"""

import threading
from pathlib import Path
from typing import Callable

from loguru import logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .loader import ConfigurationLoader
from .models import RepositoryConfig


class ConfigurationChangeHandler(FileSystemEventHandler):
    """Handle configuration file changes."""

    def __init__(self, config_path: Path, callback: Callable[[RepositoryConfig], None]):
        """
        Initialize the change handler.

        Args:
            config_path: Path to configuration directory or file
            callback: Function to call when configuration changes
        """
        self.config_path = config_path
        self.callback = callback
        self.loader = ConfigurationLoader(str(config_path))
        self._lock = threading.Lock()
        self._last_reload_time = 0
        self._reload_cooldown = 1.0  # seconds

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Check if the modified file is a config file
        if not self._is_config_file(event.src_path):
            return

        # Avoid rapid reloads
        import time

        current_time = time.time()
        if current_time - self._last_reload_time < self._reload_cooldown:
            return

        self._last_reload_time = current_time
        self._reload_configuration()

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and self._is_config_file(event.src_path):
            self._reload_configuration()

    def on_deleted(self, event):
        """Handle file deletion events."""
        if not event.is_directory and self._is_config_file(event.src_path):
            logger.warning(f"Configuration file deleted: {event.src_path}")
            self._reload_configuration()

    def _is_config_file(self, path: str) -> bool:
        """Check if a file is a configuration file."""
        path_obj = Path(path)
        
        # Check if it's a JSON file
        if path_obj.suffix != ".json":
            return False
        
        # Ignore schema files
        if "schema" in str(path_obj):
            return False
        
        # Check if it's in the config directory
        if self.config_path.is_dir():
            return str(self.config_path) in str(path_obj)
        else:
            # Single file mode
            return str(self.config_path) == str(path_obj)

    def _reload_configuration(self):
        """Reload the configuration and notify callback."""
        with self._lock:
            try:
                logger.info("Reloading configuration...")
                
                # Clear loader cache
                self.loader._loaded_configs.clear()
                self.loader._resolved_repos.clear()
                
                # Reload configuration
                new_config = self.loader.load_config()
                
                # Call callback with new configuration
                self.callback(new_config)
                
                logger.info(
                    f"Configuration reloaded successfully. "
                    f"Loaded {len(new_config.repositories)} repositories"
                )
            except Exception as e:
                logger.error(f"Failed to reload configuration: {e}")


class ConfigurationWatcher:
    """Watch configuration files for changes and reload automatically."""

    def __init__(
        self,
        config_path: str = "config",
        callback: Callable[[RepositoryConfig], None] | None = None,
    ):
        """
        Initialize the configuration watcher.

        Args:
            config_path: Path to configuration directory or file
            callback: Function to call when configuration changes
        """
        self.config_path = Path(config_path)
        self.callback = callback
        self.observer = Observer()
        self.handler = ConfigurationChangeHandler(self.config_path, self._on_config_change)
        self._user_callback = callback
        self._started = False

    def _on_config_change(self, new_config: RepositoryConfig):
        """Internal callback for configuration changes."""
        if self._user_callback:
            try:
                self._user_callback(new_config)
            except Exception as e:
                logger.error(f"Error in configuration change callback: {e}")

    def start(self):
        """Start watching for configuration changes."""
        if self._started:
            logger.warning("Configuration watcher already started")
            return

        # Determine what to watch
        if self.config_path.is_dir():
            # Watch the entire directory
            watch_path = self.config_path
        else:
            # Watch the parent directory for single file
            watch_path = self.config_path.parent

        # Schedule the observer
        self.observer.schedule(self.handler, str(watch_path), recursive=True)
        self.observer.start()
        self._started = True
        
        logger.info(f"Started watching configuration at: {watch_path}")

    def stop(self):
        """Stop watching for configuration changes."""
        if not self._started:
            return

        self.observer.stop()
        self.observer.join()
        self._started = False
        
        logger.info("Stopped configuration watcher")

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


def watch_config(
    config_path: str = "config",
    callback: Callable[[RepositoryConfig], None] | None = None,
) -> ConfigurationWatcher:
    """
    Create and start a configuration watcher.

    Args:
        config_path: Path to configuration directory or file
        callback: Function to call when configuration changes

    Returns:
        ConfigurationWatcher instance

    Example:
        ```python
        def on_config_change(new_config):
            print(f"Config updated: {len(new_config.repositories)} repos")

        watcher = watch_config("config", on_config_change)
        watcher.start()
        
        # ... do work ...
        
        watcher.stop()
        ```
    """
    return ConfigurationWatcher(config_path, callback)