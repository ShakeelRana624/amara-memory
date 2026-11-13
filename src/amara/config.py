"""Configuration management for AMARA framework."""

from __future__ import annotations

import enum
import os
from collections.abc import Mapping

from pydantic import BaseModel, ConfigDict, Field, field_validator

from amara.exceptions import ConfigurationError


class StorageBackendType(enum.StrEnum):
    """Supported storage backend types."""

    IN_MEMORY = "in_memory"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


class StorageConfig(BaseModel):
    """Configuration for persistence storage engines."""

    model_config = ConfigDict(frozen=True)

    backend: StorageBackendType = Field(default=StorageBackendType.IN_MEMORY)
    connection_uri: str | None = Field(default=None)
    max_connections: int = Field(default=10, ge=1, le=100)
    table_name: str = Field(default="memory_records", min_length=1)
    vector_dimension: int = Field(default=1536, ge=1)
    in_memory_max_records: int = Field(default=100_000, ge=100)


class SecurityConfig(BaseModel):
    """Configuration for security, isolation, and sanitization."""

    model_config = ConfigDict(frozen=True)

    enforce_tenant_isolation: bool = Field(default=True)
    sanitize_secrets: bool = Field(default=True)
    secret_entropy_threshold: float = Field(default=4.5, ge=1.0, le=8.0)
    enable_audit_logging: bool = Field(default=True)


class DecayConfig(BaseModel):
    """Configuration for cognitive decay and forgetting curves."""

    model_config = ConfigDict(frozen=True)

    decay_rate: float = Field(default=0.5, ge=0.01, le=2.0)
    active_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    archive_days: int = Field(default=90, ge=1)


class AmaraConfig(BaseModel):
    """Root configuration model for AMARA."""

    model_config = ConfigDict(frozen=True)

    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    storage: StorageConfig = Field(default_factory=StorageConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    decay: DecayConfig = Field(default_factory=DecayConfig)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        valid_envs = {"development", "testing", "staging", "production"}
        v_clean = v.strip().lower()
        if v_clean not in valid_envs:
            raise ValueError(f"Invalid environment '{v}'. Must be one of {valid_envs}.")
        return v_clean

    @classmethod
    def from_env(cls, env_overrides: Mapping[str, str] | None = None) -> AmaraConfig:
        """Load configuration from environment variables with AMARA_ prefix."""
        env = dict(env_overrides if env_overrides is not None else os.environ)

        storage_backend_str = env.get("AMARA_STORAGE_BACKEND", "in_memory").lower()
        try:
            storage_backend = StorageBackendType(storage_backend_str)
        except ValueError as exc:
            raise ConfigurationError(
                f"Unsupported storage backend: '{storage_backend_str}'. "
                f"Valid choices: {[b.value for b in StorageBackendType]}"
            ) from exc

        try:
            storage_cfg = StorageConfig(
                backend=storage_backend,
                connection_uri=env.get("AMARA_STORAGE_URI"),
                max_connections=int(env.get("AMARA_STORAGE_MAX_CONNECTIONS", "10")),
                vector_dimension=int(env.get("AMARA_VECTOR_DIMENSION", "1536")),
                in_memory_max_records=int(env.get("AMARA_IN_MEMORY_MAX_RECORDS", "100000")),
            )

            security_cfg = SecurityConfig(
                enforce_tenant_isolation=env.get("AMARA_ENFORCE_TENANT_ISOLATION", "true").lower()
                == "true",
                sanitize_secrets=env.get("AMARA_SANITIZE_SECRETS", "true").lower() == "true",
                secret_entropy_threshold=float(env.get("AMARA_SECRET_ENTROPY_THRESHOLD", "4.5")),
                enable_audit_logging=env.get("AMARA_ENABLE_AUDIT_LOGGING", "true").lower()
                == "true",
            )

            decay_cfg = DecayConfig(
                decay_rate=float(env.get("AMARA_DECAY_RATE", "0.5")),
                active_threshold=float(env.get("AMARA_ACTIVE_THRESHOLD", "0.3")),
                archive_days=int(env.get("AMARA_ARCHIVE_DAYS", "90")),
            )

            return cls(
                environment=env.get("AMARA_ENV", "development"),
                log_level=env.get("AMARA_LOG_LEVEL", "INFO").upper(),
                storage=storage_cfg,
                security=security_cfg,
                decay=decay_cfg,
            )
        except (ValueError, TypeError) as exc:
            raise ConfigurationError(f"Failed to parse AMARA configuration: {exc}") from exc
