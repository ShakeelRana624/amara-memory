"""Tests for AMARA configuration management and environment parsing."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from amara.config import AmaraConfig, StorageBackendType
from amara.exceptions import ConfigurationError


def test_default_configuration() -> None:
    """Verify default configuration values."""
    config = AmaraConfig()

    assert config.environment == "development"
    assert config.log_level == "INFO"
    assert config.storage.backend == StorageBackendType.IN_MEMORY
    assert config.storage.vector_dimension == 1536
    assert config.security.enforce_tenant_isolation is True
    assert config.security.sanitize_secrets is True
    assert config.decay.decay_rate == 0.5


def test_config_from_env_defaults() -> None:
    """Test loading configuration from empty environment dictionary."""
    config = AmaraConfig.from_env(env_overrides={})

    assert config.environment == "development"
    assert config.storage.backend == StorageBackendType.IN_MEMORY


def test_config_from_env_with_custom_values() -> None:
    """Test environment overrides parsing."""
    custom_env = {
        "AMARA_ENV": "production",
        "AMARA_LOG_LEVEL": "WARNING",
        "AMARA_STORAGE_BACKEND": "postgresql",
        "AMARA_STORAGE_URI": "postgresql://user:pass@localhost:5432/amara_prod",
        "AMARA_STORAGE_MAX_CONNECTIONS": "25",
        "AMARA_VECTOR_DIMENSION": "3072",
        "AMARA_ENFORCE_TENANT_ISOLATION": "true",
        "AMARA_SANITIZE_SECRETS": "false",
        "AMARA_DECAY_RATE": "0.75",
        "AMARA_ACTIVE_THRESHOLD": "0.4",
        "AMARA_ARCHIVE_DAYS": "120",
    }

    config = AmaraConfig.from_env(env_overrides=custom_env)

    assert config.environment == "production"
    assert config.log_level == "WARNING"
    assert config.storage.backend == StorageBackendType.POSTGRESQL
    assert config.storage.connection_uri == "postgresql://user:pass@localhost:5432/amara_prod"
    assert config.storage.max_connections == 25
    assert config.storage.vector_dimension == 3072
    assert config.security.sanitize_secrets is False
    assert config.decay.decay_rate == 0.75
    assert config.decay.active_threshold == 0.4
    assert config.decay.archive_days == 120


def test_config_rejects_invalid_environment() -> None:
    """Ensure invalid environment names are rejected."""
    with pytest.raises(ValidationError, match="Invalid environment"):
        AmaraConfig(environment="invalid_env_name")


def test_config_rejects_unsupported_storage_backend() -> None:
    """Ensure unsupported backend strings raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="Unsupported storage backend"):
        AmaraConfig.from_env(env_overrides={"AMARA_STORAGE_BACKEND": "couchdb"})


def test_config_rejects_malformed_numeric_env() -> None:
    """Ensure invalid numbers in env variables raise ConfigurationError."""
    with pytest.raises(ConfigurationError, match="Failed to parse AMARA configuration"):
        AmaraConfig.from_env(env_overrides={"AMARA_STORAGE_MAX_CONNECTIONS": "not_a_number"})
