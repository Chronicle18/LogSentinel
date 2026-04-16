import os
import yaml
import structlog
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ValidationError
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

log = structlog.get_logger()

class TransformRule(BaseModel):
    name: str
    pattern: str
    fields: List[str]
    static_fields: Dict[str, str] = Field(default_factory=dict)

class SourcetypeConfig(BaseModel):
    sourcetype: str
    time_format: str
    transforms: List[TransformRule]
    cim_mapping: Dict[str, str] = Field(default_factory=dict)
    default_severity: str = "medium"

class ConfigManager(FileSystemEventHandler):
    def __init__(self, config_dir: str):
        self.config_dir = config_dir
        self.configs: Dict[str, SourcetypeConfig] = {}
        self.observer = Observer()
        self._load_all()

    def _load_all(self):
        if not os.path.exists(self.config_dir):
            log.warning("config_dir_not_found", dir=self.config_dir)
            return
            
        for filename in os.listdir(self.config_dir):
            if filename.endswith((".yaml", ".yml")):
                self._load_config(os.path.join(self.config_dir, filename))

    def _load_config(self, filepath: str):
        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                log.warning("empty_config", filepath=filepath)
                return

            config = SourcetypeConfig(**data)
            self.configs[config.sourcetype] = config
            log.info("config_loaded", sourcetype=config.sourcetype, filepath=filepath)
        except ValidationError as e:
            log.error("config_validation_error", filepath=filepath, errors=e.errors())
        except Exception as e:
            log.error("config_load_error", filepath=filepath, error=str(e))

    def get_config(self, sourcetype: str) -> Optional[SourcetypeConfig]:
        return self.configs.get(sourcetype)

    def start_watching(self):
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
        self.observer.schedule(self, path=self.config_dir, recursive=False)
        self.observer.start()
        log.info("config_watcher_started", dir=self.config_dir)

    def stop_watching(self):
        if self.observer.is_alive():
            self.observer.stop()
            self.observer.join()

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(('.yaml', '.yml')):
            log.info("config_file_modified", filepath=event.src_path)
            self._load_config(event.src_path)

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(('.yaml', '.yml')):
            log.info("config_file_created", filepath=event.src_path)
            self._load_config(event.src_path)
