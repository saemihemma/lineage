"""Tests for anti-cheat mechanisms"""
import pytest
import time
from core.anticheat import (
    generate_outcome_signature,
    verify_outcome_signature,
    generate_expedition_seed,
    validate_timer_completion,
    detect_anomalies,
    record_action,
    check_and_flag_anomaly
)


class TestHMACOutcomeSigning:
    """Test HMAC signature generation and verification"""

    def test_generate_signature_deterministic(self):
        """Test that signature generation is deterministic"""
        session_id = "test-session-123"
        expedition_id = "exp-456"
        start_ts = 1234567890.123456
        outcome_data = {
            "result": "success",
            "clone_id": "clone-1",
            "expedition_kind": "MINING",
            "loot": {"Tritanium": 5, "Metal Ore": 3},
            "xp_gained": 10,
            "survived": True
        }

        sig1 = generate_outcome_signature(session_id, expedition_id, start_ts, outcome_data)
        sig2 = generate_outcome_signature(session_id, expedition_id, start_ts, outcome_data)

        assert sig1 == sig2, "Signature should be deterministic"
        assert len(sig1) == 64, "SHA256 hex digest should be 64 characters"

    def test_signature_changes_with_different_data(self):
        """Test that changing any parameter changes the signature"""
        session_id = "test-session-123"
        expedition_id = "exp-456"
        start_ts = 1234567890.123456
        outcome_data = {
            "result": "success",
            "clone_id": "clone-1",
            "expedition_kind": "MINING",
            "loot": {"Tritanium": 5},
            "xp_gained": 10,
            "survived": True
        }

        sig_original = generate_outcome_signature(session_id, expedition_id, start_ts, outcome_data)

        # Change session_id
        sig_session = generate_outcome_signature("different-session", expedition_id, start_ts, outcome_data)
        assert sig_session != sig_original

        # Change expedition_id
        sig_expedition = generate_outcome_signature(session_id, "different-exp", start_ts, outcome_data)
        assert sig_expedition != sig_original

        # Change timestamp
        sig_ts = generate_outcome_signature(session_id, expedition_id, start_ts + 1.0, outcome_data)
        assert sig_ts != sig_original

        # Change outcome data
        tampered_data = outcome_data.copy()
        tampered_data["xp_gained"] = 1000  # Cheating!
        sig_tampered = generate_outcome_signature(session_id, expedition_id, start_ts, tampered_data)
        assert sig_tampered != sig_original

    def test_verify_valid_signature(self):
        """Test verification of valid signature"""
        session_id = "test-session-123"
        expedition_id = "exp-456"
        start_ts = 1234567890.123456
        outcome_data = {
            "result": "success",
            "clone_id": "clone-1",
            "expedition_kind": "MINING",
            "loot": {"Tritanium": 5},
            "xp_gained": 10,
            "survived": True
        }

        signature = generate_outcome_signature(session_id, expedition_id, start_ts, outcome_data)
        is_valid = verify_outcome_signature(session_id, expedition_id, start_ts, outcome_data, signature)

        assert is_valid is True

    def test_verify_tampered_signature(self):
        """Test that tampered data fails verification"""
        session_id = "test-session-123"
        expedition_id = "exp-456"
        start_ts = 1234567890.123456
        outcome_data = {
            "result": "success",
            "clone_id": "clone-1",
            "expedition_kind": "MINING",
            "loot": {"Tritanium": 5},
            "xp_gained": 10,
            "survived": True
        }

        # Generate legitimate signature
        signature = generate_outcome_signature(session_id, expedition_id, start_ts, outcome_data)

        # Tamper with data
        tampered_data = outcome_data.copy()
        tampered_data["xp_gained"] = 1000  # Cheating!

        # Verification should fail
        is_valid = verify_outcome_signature(session_id, expedition_id, start_ts, tampered_data, signature)

        assert is_valid is False

    def test_verify_wrong_signature(self):
        """Test that wrong signature fails verification"""
        session_id = "test-session-123"
        expedition_id = "exp-456"
        start_ts = 1234567890.123456
        outcome_data = {
            "result": "success",
            "clone_id": "clone-1",
            "expedition_kind": "MINING",
            "loot": {"Tritanium": 5},
            "xp_gained": 10,
            "survived": True
        }

        wrong_signature = "0" * 64  # Fake signature

        is_valid = verify_outcome_signature(session_id, expedition_id, start_ts, outcome_data, wrong_signature)

        assert is_valid is False


class TestExpeditionSeed:
    """Test deterministic RNG seed generation"""

    def test_generate_seed_deterministic(self):
        """Test that seed generation is deterministic"""
        session_id = "test-session-123"
        expedition_id = "exp-456"
        start_ts = 1234567890.123456

        seed1 = generate_expedition_seed(session_id, expedition_id, start_ts)
        seed2 = generate_expedition_seed(session_id, expedition_id, start_ts)

        assert seed1 == seed2, "Seed should be deterministic"
        assert isinstance(seed1, int), "Seed should be an integer"
        assert 0 <= seed1 < 2**31 - 1, "Seed should be in valid range"

    def test_different_inputs_different_seeds(self):
        """Test that different inputs produce different seeds"""
        seed1 = generate_expedition_seed("session-1", "exp-1", 1234567890.0)
        seed2 = generate_expedition_seed("session-2", "exp-1", 1234567890.0)
        seed3 = generate_expedition_seed("session-1", "exp-2", 1234567890.0)
        seed4 = generate_expedition_seed("session-1", "exp-1", 1234567891.0)

        # All seeds should be different
        assert len(set([seed1, seed2, seed3, seed4])) == 4


class TestTimerValidation:
    """Test timer completion validation"""

    def test_timer_valid_completion(self):
        """Test that valid timer completion passes"""
        start_time = time.time()
        duration = 30.0
        current_time = start_time + 30.5  # Completed after duration

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        assert is_valid is True
        assert error is None

    def test_timer_cannot_complete_early(self):
        """Test that early completion is rejected"""
        start_time = time.time()
        duration = 30.0
        current_time = start_time + 20.0  # Too early!

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        assert is_valid is False
        assert "cannot complete before duration" in error.lower()

    def test_timer_tolerates_network_delay(self):
        """Test that 1s tolerance for network delay works"""
        start_time = time.time()
        duration = 30.0
        current_time = start_time + 29.5  # 0.5s early, within tolerance

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        assert is_valid is True

    def test_timer_very_late_completion_logs_warning(self):
        """Test that very late completion is allowed but logged"""
        start_time = time.time()
        duration = 30.0
        current_time = start_time + 700.0  # 11+ minutes late (>10 min grace)

        # Should still pass (user may have closed tab), but logs warning
        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        assert is_valid is True  # Allowed
        assert error is None


class TestAnomalyDetection:
    """Test anomaly detection heuristics"""

    def test_expedition_rate_normal(self):
        """Test that normal expedition rate is OK"""
        anomaly = detect_anomalies("session-1", "expedition", 60.0)  # 60/hour is reasonable
        assert anomaly is None

    def test_expedition_rate_too_high(self):
        """Test that suspiciously high expedition rate is flagged"""
        anomaly = detect_anomalies("session-1", "expedition", 200.0)  # 200/hour is impossible

        assert anomaly is not None
        assert "too high" in anomaly.lower()
        assert "150" in anomaly or "200" in anomaly

    def test_gather_rate_normal(self):
        """Test that normal gather rate is OK"""
        anomaly = detect_anomalies("session-1", "gather", 200.0)  # 200/hour is reasonable
        assert anomaly is None

    def test_gather_rate_too_high(self):
        """Test that suspiciously high gather rate is flagged"""
        anomaly = detect_anomalies("session-1", "gather", 500.0)  # 500/hour is impossible

        assert anomaly is not None
        assert "too high" in anomaly.lower()

    def test_clone_grow_rate_normal(self):
        """Test that normal clone grow rate is OK"""
        anomaly = detect_anomalies("session-1", "grow_clone", 50.0)  # 50/hour is reasonable
        assert anomaly is None

    def test_clone_grow_rate_too_high(self):
        """Test that suspiciously high clone grow rate is flagged"""
        anomaly = detect_anomalies("session-1", "grow_clone", 100.0)  # 100/hour is impossible

        assert anomaly is not None
        assert "too high" in anomaly.lower()

    def test_survival_rate_normal(self):
        """Test that normal survival rate (~80%) is OK"""
        outcome_stats = {"success_rate": 0.80}
        anomaly = detect_anomalies("session-1", "expedition", 60.0, outcome_stats)

        assert anomaly is None

    def test_survival_rate_suspiciously_high(self):
        """Test that suspiciously high survival rate (>95%) is flagged"""
        outcome_stats = {"success_rate": 0.98}
        anomaly = detect_anomalies("session-1", "expedition", 60.0, outcome_stats)

        assert anomaly is not None
        assert "survival rate" in anomaly.lower()


class TestActionRateTracking:
    """Test action rate tracking"""

    def test_record_action_calculates_rate(self):
        """Test that recording actions calculates rate correctly"""
        session_id = "test-session"
        action_type = "test_action"

        # Record 5 actions
        for _ in range(5):
            rate = record_action(session_id, action_type)

        assert rate == 5, "Should have 5 actions in last hour"

    def test_action_history_cleanup(self):
        """Test that old actions are cleaned up"""
        session_id = "test-session"
        action_type = "test_action"
        now = time.time()

        # Record old action (2 hours ago)
        record_action(session_id, action_type, now - 7200)

        # Record new action (now)
        rate = record_action(session_id, action_type, now)

        # Old action should be cleaned up
        assert rate == 1, "Old actions should be removed"
