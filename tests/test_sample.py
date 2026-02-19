import pytest

from utils import add, subtract


# ---------------------------------------------------------------------------
# add()
# ---------------------------------------------------------------------------


class TestAdd:
    def test_positive_numbers(self):
        assert add(1, 2) == 3

    def test_zero_plus_zero(self):
        assert add(0, 0) == 0

    def test_zero_identity(self):
        assert add(5, 0) == 5
        assert add(0, 5) == 5

    def test_negative_numbers(self):
        assert add(-1, -2) == -3

    def test_mixed_sign(self):
        assert add(-3, 5) == 2
        assert add(3, -5) == -2

    def test_large_numbers(self):
        assert add(1_000_000, 2_000_000) == 3_000_000

    def test_commutative(self):
        """add(a, b) must equal add(b, a) for all inputs."""
        pairs = [(1, 2), (-1, 3), (0, 7), (100, -100)]
        for a, b in pairs:
            assert add(a, b) == add(b, a), f"commutativity failed for add({a}, {b})"

    @pytest.mark.parametrize(
        "a, b, expected",
        [
            (2, 2, 4),
            (-5, -5, -10),
            (0, -1, -1),
            (1_000, 999, 1_999),
        ],
    )
    def test_parametrized(self, a, b, expected):
        assert add(a, b) == expected


# ---------------------------------------------------------------------------
# subtract()
# ---------------------------------------------------------------------------


class TestSubtract:
    def test_positive_numbers(self):
        assert subtract(1, 2) == -1

    def test_zero_minus_zero(self):
        assert subtract(0, 0) == 0

    def test_zero_identity(self):
        """Subtracting 0 should return the original value."""
        assert subtract(5, 0) == 5
        assert subtract(-5, 0) == -5

    def test_self_subtraction(self):
        """Any number minus itself should be 0."""
        for n in [-100, -1, 0, 1, 100]:
            assert subtract(n, n) == 0, f"subtract({n}, {n}) != 0"

    def test_negative_numbers(self):
        assert subtract(-1, -2) == 1

    def test_mixed_sign(self):
        assert subtract(3, -2) == 5
        assert subtract(-3, 2) == -5

    def test_large_numbers(self):
        assert subtract(2_000_000, 1_000_000) == 1_000_000

    def test_not_commutative(self):
        """subtract(a, b) must NOT equal subtract(b, a) when a != b."""
        assert subtract(5, 3) != subtract(3, 5)

    @pytest.mark.parametrize(
        "a, b, expected",
        [
            (10, 3, 7),
            (0, 5, -5),
            (-4, -4, 0),
            (1_000, 1, 999),
        ],
    )
    def test_parametrized(self, a, b, expected):
        assert subtract(a, b) == expected
