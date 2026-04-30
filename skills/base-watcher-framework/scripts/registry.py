#!/usr/bin/env python3
"""
WatcherRegistry - Central management for multiple watchers.

Provides registration, lifecycle management, and coordination of watchers.
Supports dynamic watcher loading and centralized event handling.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Callable, Optional, Type
from pathlib import Path
import json
import yaml

from base_watcher import BaseWatcher, WatcherConfig, WatcherEvent, WatcherState

logger = logging.getLogger(__name__)


@dataclass
class RegistryStats:
    """Statistics about registry state."""
    total_watchers: int = 0
    running: int = 0
    paused: int = 0
    stopped: int = 0
    errors: int = 0
    total_events: int = 0


class WatcherRegistry:
    """
    Central registry for managing multiple watchers.
    
    Features:
    - Register and unregister watchers
    - Start/stop all or individual watchers
    - Central event and error handling
    - Load watchers from configuration files
    
    Example:
        registry = WatcherRegistry()
        
        # Register watchers
        registry.register(my_fs_watcher)
        registry.register(my_api_watcher)
        
        # Central event handling
        registry.on_event(lambda e: emit_to_obsidian(e))
        
        # Start all
        await registry.start_all()
        
        # Graceful shutdown
        await registry.stop_all()
    """
    
    def __init__(self):
        self._watchers: dict[str, BaseWatcher] = {}
        self._watcher_types: dict[str, Type[BaseWatcher]] = {}
        self._event_handlers: list[Callable[[WatcherEvent], None]] = []
        self._error_handlers: list[Callable[[str, Exception], None]] = []
        self._stats = RegistryStats()
    
    def register_type(self, name: str, watcher_class: Type[BaseWatcher]) -> "WatcherRegistry":
        """
        Register a watcher type for dynamic instantiation.
        
        Args:
            name: Type identifier (e.g., "filesystem", "api")
            watcher_class: BaseWatcher subclass
            
        Returns:
            Self for chaining
        """
        self._watcher_types[name] = watcher_class
        logger.info(f"Registered watcher type: {name}")
        return self
    
    def register(self, watcher: BaseWatcher) -> "WatcherRegistry":
        """
        Register a watcher instance.
        
        Args:
            watcher: Configured BaseWatcher instance
            
        Returns:
            Self for chaining
            
        Raises:
            ValueError: If watcher with same name already registered
        """
        if watcher.name in self._watchers:
            raise ValueError(f"Watcher '{watcher.name}' already registered")
        
        # Wire up central handlers
        watcher.on_event(self._handle_event)
        watcher.on_error(lambda e: self._handle_error(watcher.name, e))
        
        self._watchers[watcher.name] = watcher
        self._stats.total_watchers += 1
        logger.info(f"Registered watcher: {watcher.name}")
        
        return self
    
    def unregister(self, name: str) -> Optional[BaseWatcher]:
        """
        Unregister a watcher by name.
        
        Args:
            name: Watcher name
            
        Returns:
            The unregistered watcher, or None if not found
        """
        watcher = self._watchers.pop(name, None)
        if watcher:
            self._stats.total_watchers -= 1
            logger.info(f"Unregistered watcher: {name}")
        return watcher
    
    def get(self, name: str) -> Optional[BaseWatcher]:
        """Get a watcher by name."""
        return self._watchers.get(name)
    
    def list_watchers(self) -> list[str]:
        """List all registered watcher names."""
        return list(self._watchers.keys())
    
    def on_event(self, handler: Callable[[WatcherEvent], None]) -> "WatcherRegistry":
        """
        Register central event handler.
        
        Args:
            handler: Callback receiving all events from all watchers
            
        Returns:
            Self for chaining
        """
        self._event_handlers.append(handler)
        return self
    
    def on_error(self, handler: Callable[[str, Exception], None]) -> "WatcherRegistry":
        """
        Register central error handler.
        
        Args:
            handler: Callback(watcher_name, exception) for all errors
            
        Returns:
            Self for chaining
        """
        self._error_handlers.append(handler)
        return self
    
    async def start(self, name: str) -> None:
        """Start a specific watcher by name."""
        watcher = self._watchers.get(name)
        if not watcher:
            raise KeyError(f"Watcher '{name}' not found")
        
        await watcher.start()
        self._update_stats()
    
    async def stop(self, name: str) -> None:
        """Stop a specific watcher by name."""
        watcher = self._watchers.get(name)
        if not watcher:
            raise KeyError(f"Watcher '{name}' not found")
        
        await watcher.stop()
        self._update_stats()
    
    async def start_all(self) -> None:
        """Start all registered watchers concurrently."""
        tasks = [w.start() for w in self._watchers.values() if w.config.enabled]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._update_stats()
        logger.info(f"Started {len(tasks)} watchers")
    
    async def stop_all(self) -> None:
        """Stop all running watchers gracefully."""
        tasks = [w.stop() for w in self._watchers.values() if w.is_running]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._update_stats()
        logger.info("All watchers stopped")
    
    async def pause_all(self) -> None:
        """Pause all running watchers."""
        for watcher in self._watchers.values():
            if watcher.state == WatcherState.RUNNING:
                await watcher.pause()
        self._update_stats()
    
    async def resume_all(self) -> None:
        """Resume all paused watchers."""
        for watcher in self._watchers.values():
            if watcher.state == WatcherState.PAUSED:
                await watcher.resume()
        self._update_stats()
    
    def get_stats(self) -> RegistryStats:
        """Get current registry statistics."""
        self._update_stats()
        return self._stats
    
    def status(self) -> dict[str, str]:
        """Get status of all watchers."""
        return {name: w.state.value for name, w in self._watchers.items()}
    
    def load_from_config(self, config_path: str) -> "WatcherRegistry":
        """
        Load watchers from a configuration file.
        
        Supports JSON and YAML formats. Configuration structure:
        
        watchers:
          - type: filesystem
            name: docs-watcher
            config:
              watch_path: /path/to/docs
              patterns: ["*.md"]
          - type: api
            name: github-watcher
            config:
              url: https://api.github.com/...
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Self for chaining
        """
        path = Path(config_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        content = path.read_text()
        
        if path.suffix in (".yaml", ".yml"):
            try:
                config = yaml.safe_load(content)
            except ImportError:
                raise ImportError("PyYAML required for YAML config: pip install pyyaml")
        else:
            config = json.loads(content)
        
        for watcher_spec in config.get("watchers", []):
            watcher_type = watcher_spec.get("type")
            watcher_name = watcher_spec.get("name")
            watcher_config = watcher_spec.get("config", {})
            
            if watcher_type not in self._watcher_types:
                logger.warning(f"Unknown watcher type: {watcher_type}")
                continue
            
            watcher_class = self._watcher_types[watcher_type]
            
            # Get the config class from the watcher (assumes pattern)
            config_class = WatcherConfig
            if hasattr(watcher_class, "__init__"):
                import inspect
                sig = inspect.signature(watcher_class.__init__)
                for param in sig.parameters.values():
                    if param.annotation and param.annotation != inspect.Parameter.empty:
                        if hasattr(param.annotation, "__dataclass_fields__"):
                            config_class = param.annotation
                            break
            
            # Create config instance
            watcher_config["name"] = watcher_name
            cfg = config_class(**watcher_config)
            
            # Create and register watcher
            watcher = watcher_class(cfg)
            self.register(watcher)
        
        return self
    
    def _handle_event(self, event: WatcherEvent) -> None:
        """Central event dispatcher."""
        self._stats.total_events += 1
        
        for handler in self._event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")
    
    def _handle_error(self, watcher_name: str, error: Exception) -> None:
        """Central error dispatcher."""
        self._stats.errors += 1
        logger.error(f"Error in watcher '{watcher_name}': {error}")
        
        for handler in self._error_handlers:
            try:
                handler(watcher_name, error)
            except Exception as e:
                logger.error(f"Error in error handler: {e}")
    
    def _update_stats(self) -> None:
        """Update registry statistics."""
        self._stats.running = sum(
            1 for w in self._watchers.values() if w.state == WatcherState.RUNNING
        )
        self._stats.paused = sum(
            1 for w in self._watchers.values() if w.state == WatcherState.PAUSED
        )
        self._stats.stopped = sum(
            1 for w in self._watchers.values() if w.state == WatcherState.STOPPED
        )


# Global registry singleton
_registry: Optional[WatcherRegistry] = None


def get_registry() -> WatcherRegistry:
    """Get or create the global registry singleton."""
    global _registry
    if _registry is None:
        _registry = WatcherRegistry()
    return _registry
