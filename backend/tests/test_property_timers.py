"""Property-based tests for timer validation invariants

These tests use hypothesis to generate random inputs and verify that
timer validation logic maintains critical invariants across all possible inputs.
"""
import pytest
import time
from hypothesis import given, strategies as st, assume, settings
from core.anticheat import validate_timer_completion


class TestTimerValidationProperties:
    """Property-based tests for timer validation"""

    @given(
        duration=st.floats(min_value=1.0, max_value=3600.0),
        elapsed=st.floats(min_value=0.0, max_value=4200.0)
    )
    @settings(max_examples=200)
    def test_early_completion_always_rejected(self, duration, elapsed):
        """
        Property: Timer completions earlier than (duration - 1s) are ALWAYS rejected.

        Invariant: For all durations D, if elapsed < D - 1.0, then validation fails.
        """
        assume(elapsed < duration - 1.0)  # Only test early completions

        current_time = 1000.0 + elapsed
        start_time = 1000.0

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        assert is_valid is False, f"Early completion should be rejected (elapsed={elapsed:.2f}s, duration={duration:.2f}s)"
        assert error is not None, "Error message should be provided for early completion"
        assert "cannot complete before duration" in error.lower()

    @given(
        duration=st.floats(min_value=1.0, max_value=3600.0),
        network_delay=st.floats(min_value=-1.0, max_value=1.0)
    )
    @settings(max_examples=200)
    def test_network_tolerance_accepted(self, duration, network_delay):
        """
        Property: Timer completions within network tolerance (±1s) are accepted.

        Invariant: For all durations D, if D - 1.0 <= elapsed <= D + 600,
                   then validation passes.
        """
        elapsed = duration + network_delay
        assume(elapsed >= duration - 1.0)  # Within tolerance
        assume(elapsed <= duration + 600.0)  # Within grace period

        current_time = 1000.0 + elapsed
        start_time = 1000.0

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        assert is_valid is True, f"Within tolerance should be accepted (elapsed={elapsed:.2f}s, duration={duration:.2f}s)"
        assert error is None, "No error should be returned for valid completion"

    @given(
        duration=st.floats(min_value=1.0, max_value=3600.0),
        grace_offset=st.floats(min_value=0.0, max_value=600.0)
    )
    @settings(max_examples=200)
    def test_grace_period_accepted(self, duration, grace_offset):
        """
        Property: Timer completions within grace period (up to +10 minutes) are accepted.

        Invariant: For all durations D, if D <= elapsed <= D + 600,
                   validation passes (may log warning, but doesn't fail).
        """
        elapsed = duration + grace_offset

        current_time = 1000.0 + elapsed
        start_time = 1000.0

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        assert is_valid is True, f"Within grace period should be accepted (elapsed={elapsed:.2f}s, duration={duration:.2f}s)"
        assert error is None, "Grace period completions should not return error"

    @given(
        duration=st.floats(min_value=1.0, max_value=3600.0)
    )
    @settings(max_examples=100)
    def test_exact_duration_accepted(self, duration):
        """
        Property: Timer completing at exact duration is accepted.

        Invariant: For all durations D, elapsed = D should always pass.
        """
        elapsed = duration
        current_time = 1000.0 + elapsed
        start_time = 1000.0

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        assert is_valid is True, f"Exact duration should be accepted (elapsed={elapsed:.2f}s)"
        assert error is None

    @given(
        duration=st.floats(min_value=1.0, max_value=3600.0),
        excess=st.floats(min_value=600.01, max_value=7200.0)
    )
    @settings(max_examples=200)
    def test_beyond_grace_period_accepted_with_warning(self, duration, excess):
        """
        Property: Timer completions beyond grace period are accepted (with warning).

        Invariant: For all durations D, if elapsed > D + 600, validation still passes
                   (but a warning is logged - we can't test logging in property test).
        """
        elapsed = duration + excess

        current_time = 1000.0 + elapsed
        start_time = 1000.0

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        # Should still pass (lenient for user experience)
        assert is_valid is True, f"Beyond grace period should still pass (elapsed={elapsed:.2f}s, duration={duration:.2f}s)"
        assert error is None, "No error should block late completions"

    @given(
        duration=st.floats(min_value=1.0, max_value=3600.0)
    )
    @settings(max_examples=100)
    def test_lower_boundary_accepted(self, duration):
        """
        Property: Timer at exact lower boundary (duration - 1.0) is accepted.

        Boundary test: elapsed = duration - 1.0 should be the MINIMUM accepted.
        Note: We add a tiny epsilon to avoid floating point precision issues.
        """
        # Add tiny epsilon to avoid floating point comparison issues
        # (duration - 1.0 might not exactly equal (start + duration - 1.0) - start)
        elapsed = duration - 1.0 + 0.001  # Just above boundary
        current_time = 1000.0 + elapsed
        start_time = 1000.0

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        # At exact boundary (with epsilon), should be accepted
        assert is_valid is True, f"Lower boundary should be accepted (elapsed={elapsed:.2f}s, duration={duration:.2f}s)"

    @given(
        duration=st.floats(min_value=1.0, max_value=3600.0),
        epsilon=st.floats(min_value=0.01, max_value=0.5)
    )
    @settings(max_examples=100)
    def test_just_below_boundary_rejected(self, duration, epsilon):
        """
        Property: Timer just below lower boundary is rejected.

        Boundary test: elapsed = duration - 1.0 - epsilon should be rejected.
        """
        elapsed = duration - 1.0 - epsilon
        current_time = 1000.0 + elapsed
        start_time = 1000.0

        is_valid, error = validate_timer_completion(start_time, duration, current_time)

        assert is_valid is False, f"Just below boundary should be rejected (elapsed={elapsed:.2f}s, duration={duration:.2f}s)"
        assert error is not None


class TestTimerMonotonicityProperties:
    """Test monotonicity properties of timer validation"""

    @given(
        duration=st.floats(min_value=1.0, max_value=3600.0),
        elapsed1=st.floats(min_value=0.0, max_value=4200.0),
        elapsed2=st.floats(min_value=0.0, max_value=4200.0)
    )
    @settings(max_examples=200)
    def test_monotonicity_no_fail_after_pass(self, duration, elapsed1, elapsed2):
        """
        Property: Timer validation is monotonic - if it passes at time T,
                  it must pass at all times > T.

        Invariant: For all durations D, if validate(D, elapsed1) = pass
                   and elapsed2 > elapsed1, then validate(D, elapsed2) = pass.
        """
        assume(elapsed1 < elapsed2)  # elapsed2 happens after elapsed1

        current_time1 = 1000.0 + elapsed1
        current_time2 = 1000.0 + elapsed2
        start_time = 1000.0

        is_valid1, _ = validate_timer_completion(start_time, duration, current_time1)
        is_valid2, _ = validate_timer_completion(start_time, duration, current_time2)

        # Monotonicity: If earlier check passed, later check must also pass
        if is_valid1:
            assert is_valid2, (
                f"Monotonicity violated: passed at elapsed={elapsed1:.2f}s "
                f"but failed at elapsed={elapsed2:.2f}s (duration={duration:.2f}s)"
            )


class TestTimerEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_zero_duration_timer(self):
        """Test timer with zero duration"""
        # Zero duration timer should allow immediate completion
        is_valid, error = validate_timer_completion(
            start_time=1000.0,
            duration=0.0,
            current_time=1000.0
        )

        # Should be valid (elapsed = 0, duration - 1 = -1, so 0 > -1)
        assert is_valid is True

    def test_very_short_timer(self):
        """Test timer with very short duration (< 1s)"""
        # 0.5s duration should allow completion at 0s elapsed (since tolerance is 1s)
        is_valid, error = validate_timer_completion(
            start_time=1000.0,
            duration=0.5,
            current_time=1000.0
        )

        # elapsed=0, duration=0.5, threshold=duration-1=-0.5, so 0 > -0.5 → pass
        assert is_valid is True

    def test_very_long_timer(self):
        """Test timer with very long duration (hours)"""
        # 2 hour timer
        duration = 7200.0  # 2 hours
        elapsed = 7200.0   # Exactly 2 hours

        is_valid, error = validate_timer_completion(
            start_time=1000.0,
            duration=duration,
            current_time=1000.0 + elapsed
        )

        assert is_valid is True

    def test_negative_elapsed_time(self):
        """Test timer with current_time before start_time (clock skew)"""
        # This represents a clock skew scenario
        is_valid, error = validate_timer_completion(
            start_time=1000.0,
            duration=60.0,
            current_time=999.0  # 1 second before start
        )

        # elapsed = -1.0, threshold = 60 - 1 = 59, so -1 < 59 → fail
        assert is_valid is False
        assert error is not None

    def test_exact_one_second_tolerance(self):
        """Test that exactly 1 second tolerance is respected"""
        duration = 60.0

        # At duration - 1.0 seconds: should pass
        is_valid_at_boundary, _ = validate_timer_completion(
            start_time=1000.0,
            duration=duration,
            current_time=1000.0 + 59.0  # duration - 1.0
        )
        assert is_valid_at_boundary is True

        # At duration - 1.01 seconds: should fail
        is_valid_below_boundary, _ = validate_timer_completion(
            start_time=1000.0,
            duration=duration,
            current_time=1000.0 + 58.99  # duration - 1.01
        )
        assert is_valid_below_boundary is False

    def test_exact_grace_period_boundary(self):
        """Test grace period boundary (600 seconds)"""
        duration = 60.0

        # At duration + 600 seconds: should pass (with warning)
        is_valid_at_grace, error = validate_timer_completion(
            start_time=1000.0,
            duration=duration,
            current_time=1000.0 + 660.0  # duration + 600
        )
        assert is_valid_at_grace is True
        assert error is None  # Passes, warning is only logged

        # At duration + 601 seconds: should still pass (with warning)
        is_valid_beyond_grace, error = validate_timer_completion(
            start_time=1000.0,
            duration=duration,
            current_time=1000.0 + 661.0  # duration + 601
        )
        assert is_valid_beyond_grace is True
        assert error is None  # Still passes


class TestTimerInvariants:
    """Test fundamental invariants of timer validation"""

    def test_invariant_determinism(self):
        """
        Invariant: Timer validation is deterministic - same inputs produce same outputs.
        """
        start_time = 1000.0
        duration = 60.0
        current_time = 1059.0

        # Call multiple times
        results = [
            validate_timer_completion(start_time, duration, current_time)
            for _ in range(10)
        ]

        # All results should be identical
        assert all(r == results[0] for r in results), "Timer validation should be deterministic"

    def test_invariant_independence(self):
        """
        Invariant: Timer validation depends only on elapsed time, not absolute time.
        """
        duration = 60.0
        elapsed = 59.5

        # Different start times, same elapsed
        result1 = validate_timer_completion(1000.0, duration, 1000.0 + elapsed)
        result2 = validate_timer_completion(2000.0, duration, 2000.0 + elapsed)
        result3 = validate_timer_completion(3000.0, duration, 3000.0 + elapsed)

        # All should produce same result (time-independent)
        assert result1 == result2 == result3, "Validation should depend only on elapsed time"

    def test_invariant_symmetry_around_duration(self):
        """
        Invariant: For small deltas, duration ± delta should have symmetric behavior
                   within tolerance bounds.
        """
        duration = 60.0
        start_time = 1000.0

        # Test symmetric deltas around duration (within tolerance)
        for delta in [0.1, 0.5, 0.9]:
            # Before duration
            is_valid_before, _ = validate_timer_completion(
                start_time, duration, start_time + duration - delta
            )

            # After duration
            is_valid_after, _ = validate_timer_completion(
                start_time, duration, start_time + duration + delta
            )

            # Both should be valid (within tolerance)
            assert is_valid_before is True, f"duration - {delta}s should be valid"
            assert is_valid_after is True, f"duration + {delta}s should be valid"
