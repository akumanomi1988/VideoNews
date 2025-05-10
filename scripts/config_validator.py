from typing import Dict, Any, List, Optional, Union
import json
from pathlib import Path
import logging
from dataclasses import dataclass
import re

@dataclass
class ValidationError:
    """Represents a configuration validation error"""
    path: str
    message: str
    value: Any = None

class ConfigValidator:
    """Validates pipeline configuration settings"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._schema = {
            'api_keys': {
                'type': dict,
                'required': True,
                'fields': {
                    'news_api': {'type': str, 'required': True},
                    'currents_api': {'type': str, 'required': False},
                    'pexels_api': {'type': str, 'required': True},
                    'elevenlabs': {'type': str, 'required': False}
                }
            },
            'oauth': {
                'type': dict,
                'required': True,
                'fields': {
                    'youtube': {
                        'type': dict,
                        'required': False,
                        'fields': {
                            'client_id': {'type': str, 'required': True},
                            'client_secret': {'type': str, 'required': True},
                            'redirect_uri': {'type': str, 'required': True}
                        }
                    },
                    'tiktok': {
                        'type': dict,
                        'required': False,
                        'fields': {
                            'client_key': {'type': str, 'required': True},
                            'client_secret': {'type': str, 'required': True},
                            'redirect_uri': {'type': str, 'required': True}
                        }
                    }
                }
            },
            'telegram': {
                'type': dict,
                'required': False,
                'fields': {
                    'bot_token': {'type': str, 'required': True},
                    'webhook_url': {'type': str, 'required': False},
                    'admin_chat_id': {'type': str, 'required': True}
                }
            },
            'database': {
                'type': dict,
                'required': True,
                'fields': {
                    'news_db': {'type': str, 'required': True},
                    'users_db': {'type': str, 'required': True},
                    'backup_enabled': {'type': bool, 'required': False},
                    'backup_interval_hours': {'type': int, 'required': False}
                }
            },
            'pipeline': {
                'type': dict,
                'required': True,
                'fields': {
                    'default_type': {'type': str, 'required': True, 'values': ['short', 'long']},
                    'parallel_processing': {'type': bool, 'required': False},
                    'memory_optimization': {'type': bool, 'required': False},
                    'cache_enabled': {'type': bool, 'required': False},
                    'temp_dir': {'type': str, 'required': True},
                    'output_dir': {'type': str, 'required': True},
                    'max_retries': {'type': int, 'required': False},
                    'timeout_seconds': {'type': int, 'required': False}
                }
            },
            'video': {
                'type': dict,
                'required': True,
                'fields': {
                    'short_form': {
                        'type': dict,
                        'required': True,
                        'fields': {
                            'aspect_ratio': {'type': str, 'required': True, 'pattern': r'^\d+:\d+$'},
                            'target_duration': {'type': int, 'required': True},
                            'max_duration': {'type': int, 'required': True},
                            'resolution': {'type': str, 'required': True, 'pattern': r'^\d+x\d+$'},
                            'fps': {'type': int, 'required': True},
                            'bitrate': {'type': str, 'required': True, 'pattern': r'^\d+[KMG]$'}
                        }
                    },
                    'long_form': {
                        'type': dict,
                        'required': True,
                        'fields': {
                            'aspect_ratio': {'type': str, 'required': True, 'pattern': r'^\d+:\d+$'},
                            'target_duration': {'type': int, 'required': True},
                            'max_duration': {'type': int, 'required': True},
                            'resolution': {'type': str, 'required': True, 'pattern': r'^\d+x\d+$'},
                            'fps': {'type': int, 'required': True},
                            'bitrate': {'type': str, 'required': True, 'pattern': r'^\d+[KMG]$'}
                        }
                    }
                }
            },
            'tts': {
                'type': dict,
                'required': True,
                'fields': {
                    'provider': {'type': str, 'required': True, 'values': ['edge', 'elevenlabs', 'bark']},
                    'language': {'type': str, 'required': True},
                    'voice': {'type': str, 'required': True},
                    'rate': {'type': int, 'required': False},
                    'pitch': {'type': int, 'required': False},
                    'optimize_for_low_vram': {'type': bool, 'required': False},
                    'fallback_providers': {'type': list, 'required': False},
                    'quota_management': {
                        'type': dict,
                        'required': False,
                        'fields': {
                            'elevenlabs_min_chars': {'type': int, 'required': True},
                            'max_concurrent_requests': {'type': int, 'required': True}
                        }
                    }
                }
            },
            'news': {
                'type': dict,
                'required': True,
                'fields': {
                    'sources': {'type': list, 'required': True},
                    'languages': {'type': list, 'required': True},
                    'categories': {'type': list, 'required': True},
                    'content_filters': {
                        'type': dict,
                        'required': False,
                        'fields': {
                            'min_length': {'type': int, 'required': False},
                            'max_length': {'type': int, 'required': False},
                            'exclude_keywords': {'type': list, 'required': False},
                            'require_image': {'type': bool, 'required': False}
                        }
                    }
                }
            },
            'media': {
                'type': dict,
                'required': True,
                'fields': {
                    'image_generation': {
                        'type': dict,
                        'required': True,
                        'fields': {
                            'provider': {'type': str, 'required': True},
                            'style_preset': {'type': str, 'required': False},
                            'model': {'type': str, 'required': False},
                            'fallback_provider': {'type': str, 'required': False}
                        }
                    },
                    'music': {
                        'type': dict,
                        'required': False,
                        'fields': {
                            'enabled': {'type': bool, 'required': True},
                            'volume': {'type': float, 'required': True},
                            'fade_duration': {'type': int, 'required': False},
                            'library_path': {'type': str, 'required': True}
                        }
                    }
                }
            },
            'monitoring': {
                'type': dict,
                'required': False,
                'fields': {
                    'enabled': {'type': bool, 'required': True},
                    'log_level': {'type': str, 'required': True, 'values': ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']},
                    'metrics_enabled': {'type': bool, 'required': False},
                    'dashboard_port': {'type': int, 'required': False},
                    'alert_on_error': {'type': bool, 'required': False},
                    'performance_tracking': {'type': bool, 'required': False}
                }
            },
            'upload': {
                'type': dict,
                'required': True,
                'fields': {
                    'platforms': {
                        'type': dict,
                        'required': True,
                        'fields': {
                            'youtube': {
                                'type': dict,
                                'required': False,
                                'fields': {
                                    'enabled': {'type': bool, 'required': True},
                                    'privacy': {'type': str, 'required': True, 'values': ['private', 'unlisted', 'public']},
                                    'category_id': {'type': str, 'required': True},
                                    'made_for_kids': {'type': bool, 'required': True},
                                    'tags_enabled': {'type': bool, 'required': False},
                                    'auto_thumbnails': {'type': bool, 'required': False}
                                }
                            },
                            'tiktok': {
                                'type': dict,
                                'required': False,
                                'fields': {
                                    'enabled': {'type': bool, 'required': True},
                                    'privacy': {'type': str, 'required': True, 'values': ['private', 'public']},
                                    'allow_comments': {'type': bool, 'required': False},
                                    'allow_duet': {'type': bool, 'required': False},
                                    'allow_stitch': {'type': bool, 'required': False}
                                }
                            }
                        }
                    },
                    'scheduling': {
                        'type': dict,
                        'required': False,
                        'fields': {
                            'enabled': {'type': bool, 'required': True},
                            'timezone': {'type': str, 'required': True},
                            'optimal_times': {'type': list, 'required': False},
                            'min_interval_hours': {'type': int, 'required': False}
                        }
                    }
                }
            }
        }

    def _validate_field(self, value: Any, schema: Dict[str, Any], path: str) -> List[ValidationError]:
        """Validate a single field against its schema"""
        errors = []

        # Check type
        if not isinstance(value, schema['type']):
            errors.append(ValidationError(
                path=path,
                message=f"Expected type {schema['type'].__name__}, got {type(value).__name__}",
                value=value
            ))
            return errors

        # Check allowed values if specified
        if 'values' in schema and value not in schema['values']:
            errors.append(ValidationError(
                path=path,
                message=f"Value must be one of: {', '.join(schema['values'])}",
                value=value
            ))

        # Check regex pattern if specified
        if 'pattern' in schema and isinstance(value, str):
            if not re.match(schema['pattern'], value):
                errors.append(ValidationError(
                    path=path,
                    message=f"Value must match pattern: {schema['pattern']}",
                    value=value
                ))

        # Recursively validate nested fields
        if schema['type'] == dict and 'fields' in schema:
            for field_name, field_schema in schema['fields'].items():
                field_path = f"{path}.{field_name}" if path else field_name
                
                if field_name not in value:
                    if field_schema.get('required', False):
                        errors.append(ValidationError(
                            path=field_path,
                            message="Missing required field"
                        ))
                else:
                    errors.extend(self._validate_field(value[field_name], field_schema, field_path))

        return errors

    def validate(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Validate configuration and return list of validation errors"""
        return self._validate_field(config, {'type': dict, 'fields': self._schema}, '')

    def validate_file(self, config_path: str) -> List[ValidationError]:
        """Validate configuration from file"""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            return self.validate(config)
        except json.JSONDecodeError as e:
            return [ValidationError(
                path='file',
                message=f"Invalid JSON format: {str(e)}",
                value=config_path
            )]
        except Exception as e:
            return [ValidationError(
                path='file',
                message=f"Failed to read config file: {str(e)}",
                value=config_path
            )]

    @staticmethod
    def format_errors(errors: List[ValidationError]) -> str:
        """Format validation errors into readable message"""
        if not errors:
            return "Configuration is valid"
            
        messages = ["Configuration validation failed:"]
        for error in errors:
            value_str = f" (got: {error.value})" if error.value is not None else ""
            messages.append(f"- {error.path}: {error.message}{value_str}")
        return "\n".join(messages)

    def verify_paths(self, config: Dict[str, Any]) -> List[ValidationError]:
        """Verify that all configured paths exist and are accessible"""
        errors = []
        paths_to_check = [
            ('pipeline.temp_dir', config.get('pipeline', {}).get('temp_dir'), True),
            ('pipeline.output_dir', config.get('pipeline', {}).get('output_dir'), True),
            ('media.music.library_path', config.get('media', {}).get('music', {}).get('library_path'), True),
        ]

        for path_key, path_value, is_dir in paths_to_check:
            if path_value:
                path = Path(path_value)
                if is_dir:
                    if path.exists() and not path.is_dir():
                        errors.append(ValidationError(
                            path=path_key,
                            message="Path exists but is not a directory",
                            value=path_value
                        ))
                else:
                    if not path.exists():
                        errors.append(ValidationError(
                            path=path_key,
                            message="File does not exist",
                            value=path_value
                        ))
                    elif not path.is_file():
                        errors.append(ValidationError(
                            path=path_key,
                            message="Path exists but is not a file",
                            value=path_value
                        ))

        return errors