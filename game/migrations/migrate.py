"""Migration system for game state"""
from typing import Dict, Any
import importlib
import os
import sys
from pathlib import Path


CURRENT_VERSION = 1


def migrate(state_dict: Dict[str, Any], from_version: int, to_version: int) -> Dict[str, Any]:
    """
    Migrate game state from one version to another.
    
    Args:
        state_dict: The state dictionary to migrate
        from_version: Current version of the state
        to_version: Target version to migrate to
        
    Returns:
        Migrated state dictionary
    """
    if from_version == to_version:
        return state_dict
    
    if from_version > to_version:
        raise ValueError(f"Cannot migrate backwards from version {from_version} to {to_version}")
    
    # Find migration directory
    migrations_dir = Path(__file__).parent
    
    # Apply each migration in sequence
    current = state_dict
    for version in range(from_version, to_version):
        next_version = version + 1
        migration_file = migrations_dir / f"{next_version:04d}_migration.py"
        
        if migration_file.exists():
            # Import and run migration
            module_name = f"game.migrations.{next_version:04d}_migration"
            try:
                # Remove cached module if it exists
                if module_name in sys.modules:
                    del sys.modules[module_name]
                
                migration_module = importlib.import_module(module_name)
                if hasattr(migration_module, 'migrate'):
                    current = migration_module.migrate(current)
                else:
                    raise ValueError(f"Migration {next_version:04d}_migration.py missing migrate() function")
            except Exception as e:
                raise RuntimeError(f"Failed to run migration {next_version:04d}_migration.py: {e}") from e
        else:
            # No migration file means version increment without schema change
            # Just update version number
            current['version'] = next_version
    
    current['version'] = to_version
    return current


def get_latest_version() -> int:
    """Get the latest migration version"""
    migrations_dir = Path(__file__).parent
    versions = []
    
    for file in migrations_dir.glob("*_migration.py"):
        try:
            version = int(file.stem.split('_')[0])
            versions.append(version)
        except ValueError:
            continue
    
    if not versions:
        return 1
    
    return max(versions)

