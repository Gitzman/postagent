"""Tests for reserved handles blocklist and handle format validation."""

from postagent.api.reserved import validate_handle


class TestValidHandles:
    def test_simple_handle(self):
        assert validate_handle("alice") is None

    def test_handle_with_digits(self):
        assert validate_handle("agent42") is None

    def test_handle_with_hyphens(self):
        assert validate_handle("my-agent") is None

    def test_min_length(self):
        assert validate_handle("abc") is None

    def test_max_length(self):
        assert validate_handle("a" * 32) is None

    def test_digits_only(self):
        assert validate_handle("123") is None

    def test_mixed(self):
        assert validate_handle("a1-b2-c3") is None


class TestFormatViolations:
    def test_too_short(self):
        err = validate_handle("ab")
        assert err is not None
        assert "at least 3" in err

    def test_single_char(self):
        err = validate_handle("a")
        assert err is not None
        assert "at least 3" in err

    def test_empty(self):
        err = validate_handle("")
        assert err is not None

    def test_too_long(self):
        err = validate_handle("a" * 33)
        assert err is not None
        assert "at most 32" in err

    def test_uppercase(self):
        err = validate_handle("Alice")
        assert err is not None
        assert "lowercase" in err

    def test_all_uppercase(self):
        err = validate_handle("ALICE")
        assert err is not None
        assert "lowercase" in err

    def test_special_chars(self):
        err = validate_handle("al!ce")
        assert err is not None

    def test_spaces(self):
        err = validate_handle("al ice")
        assert err is not None

    def test_underscores(self):
        err = validate_handle("my_agent")
        assert err is not None

    def test_leading_hyphen(self):
        err = validate_handle("-alice")
        assert err is not None
        assert "start or end" in err

    def test_trailing_hyphen(self):
        err = validate_handle("alice-")
        assert err is not None
        assert "start or end" in err

    def test_consecutive_hyphens(self):
        err = validate_handle("al--ice")
        assert err is not None
        assert "consecutive" in err


class TestReservedNames:
    def test_postagent(self):
        err = validate_handle("postagent")
        assert err is not None
        assert "reserved" in err

    def test_admin(self):
        err = validate_handle("admin")
        assert err is not None
        assert "reserved" in err

    def test_google(self):
        err = validate_handle("google")
        assert err is not None
        assert "reserved" in err

    def test_openai(self):
        err = validate_handle("openai")
        assert err is not None
        assert "reserved" in err

    def test_anthropic(self):
        err = validate_handle("anthropic")
        assert err is not None
        assert "reserved" in err

    def test_claude(self):
        err = validate_handle("claude")
        assert err is not None
        assert "reserved" in err

    def test_system(self):
        err = validate_handle("system")
        assert err is not None
        assert "reserved" in err


class TestNormalNamesAllowed:
    def test_not_reserved(self):
        for name in ["alice", "bob", "my-agent", "cool-bot-99", "test123"]:
            assert validate_handle(name) is None, f"{name} should be allowed"
