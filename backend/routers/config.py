"""Configuration API endpoints

Provides centralized game configuration for frontend consumption.
Supports ETag caching to minimize bandwidth and ensure config consistency.
"""
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
import hashlib
import json
from typing import Dict, Any
from core.config import CONFIG, RESOURCE_TYPES

router = APIRouter(prefix="/api/config", tags=["config"])

# Config version - increment this when making breaking changes to config structure
CONFIG_VERSION = "1.0.0"


def serialize_config() -> Dict[str, Any]:
    """
    Serialize game configuration for API consumption.

    Converts tuples to lists for JSON compatibility and organizes config
    into logical sections for frontend consumption.
    """
    # Convert tuples to lists for JSON serialization
    def convert_tuples(obj):
        if isinstance(obj, dict):
            return {k: convert_tuples(v) for k, v in obj.items()}
        elif isinstance(obj, tuple):
            return list(obj)
        elif isinstance(obj, list):
            return [convert_tuples(item) for item in obj]
        else:
            return obj

    gameplay_config = {
        "version": CONFIG_VERSION,

        # Resource configuration
        "resources": {
            "types": RESOURCE_TYPES,
            "gatherTime": convert_tuples(CONFIG["GATHER_TIME"]),
            "gatherAmount": convert_tuples(CONFIG["GATHER_AMOUNT"]),
        },

        # Clone configuration
        "clones": {
            "costs": convert_tuples(CONFIG["CLONE_COSTS"]),
            "buildTime": convert_tuples(CONFIG["CLONE_TIME"]),
        },

        # Assembler (Womb) configuration
        "assembler": {
            "cost": CONFIG["ASSEMBLER_COST"],
            "buildTime": list(CONFIG["ASSEMBLER_TIME"]),
            # Womb system configuration
            "maxDurability": CONFIG.get("WOMB_MAX_DURABILITY", 100.0),
            "maxAttention": CONFIG.get("WOMB_MAX_ATTENTION", 100.0),
            "attentionDecayPerHour": CONFIG.get("WOMB_ATTENTION_DECAY_PER_HOUR", 1.0),
            "attentionGainOnAction": CONFIG.get("WOMB_ATTENTION_GAIN_ON_ACTION", 5.0),
            "attackChance": CONFIG.get("WOMB_ATTACK_CHANCE", 0.15),
            "attackDamageMin": CONFIG.get("WOMB_ATTACK_DAMAGE_MIN", 5.0),
            "attackDamageMax": CONFIG.get("WOMB_ATTACK_DAMAGE_MAX", 15.0),
            "repairCostPerDurability": CONFIG.get("WOMB_REPAIR_COST_PER_DURABILITY", {"Tritanium": 0.5, "Metal Ore": 0.3}),
            "repairTimeMin": CONFIG.get("WOMB_REPAIR_TIME_MIN", 20),
            "repairTimeMax": CONFIG.get("WOMB_REPAIR_TIME_MAX", 40),
            "maxCount": CONFIG.get("WOMB_MAX_COUNT", 4),
            "unlockAnyPracticeL4": CONFIG.get("WOMB_UNLOCK_ANY_PRACTICE_L4", True),
            "unlockAnyPracticeL7": CONFIG.get("WOMB_UNLOCK_ANY_PRACTICE_L7", True),
            "unlockTwoPracticesL9": CONFIG.get("WOMB_UNLOCK_TWO_PRACTICES_L9", True),
            "synergyCognitiveAttentionMult": CONFIG.get("WOMB_SYNERGY_COGNITIVE_ATTENTION_MULT", 0.95),
            "synergyKineticAttackMult": CONFIG.get("WOMB_SYNERGY_KINETIC_ATTACK_MULT", 0.90),
            "synergyConstructiveRepairMult": CONFIG.get("WOMB_SYNERGY_CONSTRUCTIVE_REPAIR_MULT", 0.85),
            "synergyThreshold": CONFIG.get("WOMB_SYNERGY_THRESHOLD", 3),
        },

        # Expedition configuration
        "expeditions": {
            "rewards": convert_tuples(CONFIG["REWARDS"]),
            "deathProbability": CONFIG["DEATH_PROB"],
            "minerXpMultiplier": CONFIG.get("MINER_XP_MULT", 1.25),
        },

        # SELF progression
        "soul": {
            "startPercent": CONFIG["SOUL_START"],
            "splitBase": CONFIG["SOUL_SPLIT_BASE"],
            "splitVariance": CONFIG["SOUL_SPLIT_VARIANCE"],
            "xpRetainRange": list(CONFIG["SOUL_XP_RETAIN_RANGE"]),
            "levelStep": CONFIG["SOUL_LEVEL_STEP"],
            "levelTraitBonus": CONFIG.get("TRAIT_BASELINE_PER_LEVEL", 1),
        },

        # Practice tracks
        "practices": {
            "tracks": CONFIG["PRACTICE_TRACKS"],
            "xpPerLevel": CONFIG["PRACTICE_XP_PER_LEVEL"],
            "passiveXpPerHour": CONFIG.get("PASSIVE_XP_PER_HOUR", 5),
            "crossPollFraction": CONFIG.get("CROSS_POLL_FRACTION", 0.20),
        },

        # UI theme colors
        "theme": {
            "background": CONFIG.get("BG", "#0b0f12"),
            "panel": CONFIG.get("PANEL", "#11161a"),
            "border": CONFIG.get("BORDER", "#151a1f"),
            "text": CONFIG.get("TEXT", "#e7e7e7"),
            "muted": CONFIG.get("MUTED", "#9aa4ad"),
            "accent": CONFIG.get("ACCENT", "#ff7a00"),
            "accent2": CONFIG.get("ACCENT_2", "#ff9933"),
        },

        # Advanced configuration
        "advanced": {
            "costInflatePerLevel": CONFIG.get("COST_INFLATE_PER_LEVEL", 0.05),
            "minUploadXpThreshold": CONFIG.get("MIN_UPLOAD_XP_THRESHOLD", 50),
            "soulSafetyMargin": CONFIG.get("SOUL_SAFETY_MARGIN", 5.0),
        },
    }

    return gameplay_config


def calculate_etag(data: Dict[str, Any]) -> str:
    """Calculate ETag for config data using SHA256 hash"""
    # Serialize to stable JSON string (sorted keys)
    json_str = json.dumps(data, sort_keys=True)
    # Calculate SHA256 hash
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    # Return first 16 characters of hex digest as ETag
    return f'"{hash_obj.hexdigest()[:16]}"'


# Cache serialized config and ETag (regenerated on server restart)
_cached_config = serialize_config()
_cached_etag = calculate_etag(_cached_config)


@router.get("/gameplay")
async def get_gameplay_config(request: Request):
    """
    Get gameplay configuration with ETag support.

    Returns centralized game configuration including:
    - Resource types, gather times, amounts
    - Clone costs, build times, types
    - Expedition rewards, death probability
    - SELF progression parameters
    - UI theme colors
    - All tunable constants

    Supports conditional requests via If-None-Match header:
    - Client sends previous ETag
    - Server returns 304 Not Modified if unchanged
    - Client can cache config until ETag changes

    Example:
        GET /api/config/gameplay
        If-None-Match: "abc123def456"

        Returns:
        - 304 Not Modified (if ETag matches)
        - 200 OK with JSON config (if ETag changed or missing)
    """
    # Check if client has cached version
    client_etag = request.headers.get("If-None-Match")

    if client_etag and client_etag == _cached_etag:
        # Config hasn't changed, return 304 Not Modified
        return Response(status_code=304, headers={"ETag": _cached_etag})

    # Return config with ETag header
    return JSONResponse(
        content=_cached_config,
        headers={
            "ETag": _cached_etag,
            "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
        }
    )


@router.get("/version")
async def get_config_version():
    """
    Get current config version.

    Returns the version string and ETag for quick version checks
    without fetching full config.
    """
    return {
        "version": CONFIG_VERSION,
        "etag": _cached_etag,
    }
