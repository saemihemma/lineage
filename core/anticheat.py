"""Anti-cheat mechanisms for server-authoritative outcomes"""
import hmac
import hashlib
import secrets
import time
import os
from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

# HMAC secret key - load from environment or generate (rotatable by versioning)
# In production: Set HMAC_SECRET_KEY_V1 environment variable
# Format: HMAC_SECRET_KEY_V{version}
HMAC_KEY_VERSION = int(os.getenv("HMAC_KEY_VERSION", "1"))
HMAC_SECRET_KEY = os.getenv(f"HMAC_SECRET_KEY_V{HMAC_KEY_VERSION}")

if not HMAC_SECRET_KEY:
    # Generate a secret key for development (warn in production)
    HMAC_SECRET_KEY = secrets.token_hex(32)
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        logger.warning("⚠️  HMAC_SECRET_KEY not set! Using generated key (NOT PRODUCTION SAFE)")
    else:
        logger.info(f"Development mode: using generated HMAC key (version {HMAC_KEY_VERSION})")


def generate_outcome_signature(
    session_id: str,
    expedition_id: str,
    start_ts: float,
    outcome_data: Dict[str, Any]
) -> str:
    """
    Generate HMAC signature for expedition outcome.

    Args:
        session_id: User session identifier
        expedition_id: Unique expedition identifier
        start_ts: Server timestamp when expedition started
        outcome_data: Outcome data (result, loot, xp, etc.)

    Returns:
        Hex-encoded HMAC signature
    """
    # Create deterministic message
    message_parts = [
        session_id,
        expedition_id,
        f"{start_ts:.6f}",  # Include timestamp to prevent replay
        outcome_data.get("result", "unknown"),
        str(outcome_data.get("clone_id", "")),
        str(outcome_data.get("expedition_kind", "")),
        str(sorted(outcome_data.get("loot", {}).items())),
        str(outcome_data.get("xp_gained", 0)),
        str(outcome_data.get("survived", True)),
    ]

    message = "|".join(message_parts)

    # Generate HMAC-SHA256 signature
    signature = hmac.new(
        HMAC_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    return signature


def verify_outcome_signature(
    session_id: str,
    expedition_id: str,
    start_ts: float,
    outcome_data: Dict[str, Any],
    provided_signature: str
) -> bool:
    """
    Verify HMAC signature for expedition outcome.

    Args:
        session_id: User session identifier
        expedition_id: Unique expedition identifier
        start_ts: Server timestamp when expedition started
        outcome_data: Outcome data to verify
        provided_signature: Signature to verify against

    Returns:
        True if signature is valid, False otherwise
    """
    expected_signature = generate_outcome_signature(
        session_id,
        expedition_id,
        start_ts,
        outcome_data
    )

    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(provided_signature, expected_signature)


def generate_expedition_seed(session_id: str, expedition_id: str, start_ts: float) -> int:
    """
    Generate deterministic RNG seed for expedition using HMAC.

    This ensures:
    - Server controls randomness (client can't manipulate)
    - Outcomes are reproducible (for verification)
    - Each expedition has unique seed

    Args:
        session_id: User session identifier
        expedition_id: Unique expedition identifier
        start_ts: Server timestamp when expedition started

    Returns:
        Integer seed for RNG
    """
    message = f"{session_id}|{expedition_id}|{start_ts:.6f}"

    # Use HMAC to derive seed
    seed_hash = hmac.new(
        HMAC_SECRET_KEY.encode(),
        message.encode(),
        hashlib.sha256
    ).digest()

    # Convert first 8 bytes to integer
    seed = int.from_bytes(seed_hash[:8], byteorder='big') % (2**31 - 1)

    return seed


def validate_timer_completion(start_time: float, duration: float, current_time: float) -> Tuple[bool, Optional[str]]:
    """
    Validate that a timer has legitimately completed.

    Args:
        start_time: Server timestamp when timer started
        duration: Expected duration in seconds
        current_time: Current server timestamp

    Returns:
        Tuple of (is_valid, error_message)
    """
    elapsed = current_time - start_time

    # Timer cannot complete before duration (with 1s tolerance for network)
    if elapsed < (duration - 1.0):
        return False, f"Timer cannot complete before duration (elapsed: {elapsed:.1f}s, required: {duration:.1f}s)"

    # Timer should complete within reasonable time (duration + 10 minutes grace period)
    max_elapsed = duration + 600  # 10 minute grace for tab close/reopen
    if elapsed > max_elapsed:
        logger.warning(f"Timer completed late: {elapsed:.1f}s (expected: {duration:.1f}s)")
        # Don't fail, just log - user may have closed tab

    return True, None


def detect_anomalies(
    session_id: str,
    action_type: str,
    action_rate_per_hour: float,
    outcome_stats: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Detect anomalous behavior patterns.

    Args:
        session_id: User session identifier
        action_type: Type of action (expedition, gather, etc.)
        action_rate_per_hour: Actions per hour
        outcome_stats: Optional outcome statistics

    Returns:
        Anomaly description if detected, None otherwise
    """
    anomalies = []

    # Rate anomalies
    if action_type == "expedition":
        # Expeditions take ~30-60s minimum, so max ~60-120/hour realistic
        if action_rate_per_hour > 150:
            anomalies.append(f"Expedition rate too high: {action_rate_per_hour:.1f}/hour (max realistic: 120/hour)")

    elif action_type == "gather":
        # Gathering takes ~10-30s, so max ~120-360/hour realistic
        if action_rate_per_hour > 400:
            anomalies.append(f"Gather rate too high: {action_rate_per_hour:.1f}/hour (max realistic: 360/hour)")

    elif action_type == "grow_clone":
        # Clone growing takes ~60s, so max ~60/hour realistic
        if action_rate_per_hour > 80:
            anomalies.append(f"Clone grow rate too high: {action_rate_per_hour:.1f}/hour (max realistic: 60/hour)")

    # Outcome distribution anomalies
    if outcome_stats:
        success_rate = outcome_stats.get("success_rate", 0.0)

        # Survival rate anomaly (death_prob = 0.2, so ~80% survival expected)
        if action_type == "expedition" and success_rate > 0.95:
            anomalies.append(f"Suspiciously high survival rate: {success_rate*100:.1f}% (expected: ~80%)")

    return "; ".join(anomalies) if anomalies else None


# Action rate tracking (in-memory for now, move to Redis in production)
_action_history: Dict[str, list[float]] = {}

def record_action(session_id: str, action_type: str, timestamp: Optional[float] = None) -> float:
    """
    Record action and calculate current rate.

    Args:
        session_id: User session identifier
        action_type: Type of action
        timestamp: Optional timestamp (defaults to now)

    Returns:
        Actions per hour rate
    """
    if timestamp is None:
        timestamp = time.time()

    key = f"{session_id}:{action_type}"

    if key not in _action_history:
        _action_history[key] = []

    # Add action
    _action_history[key].append(timestamp)

    # Clean old actions (keep last hour)
    one_hour_ago = timestamp - 3600
    _action_history[key] = [t for t in _action_history[key] if t > one_hour_ago]

    # Calculate rate
    count = len(_action_history[key])
    rate_per_hour = count  # Already filtered to last hour

    return rate_per_hour


def check_and_flag_anomaly(
    session_id: str,
    action_type: str,
    outcome_stats: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """
    Check for anomalies and return flag message.

    Args:
        session_id: User session identifier
        action_type: Type of action
        outcome_stats: Optional outcome statistics

    Returns:
        Anomaly flag message if detected, None otherwise
    """
    # Record action and get rate
    rate = record_action(session_id, action_type)

    # Detect anomalies
    anomaly = detect_anomalies(session_id, action_type, rate, outcome_stats)

    if anomaly:
        logger.warning(f"🚩 Anomaly detected for session {session_id[:8]}...: {anomaly}")
        return anomaly

    return None
