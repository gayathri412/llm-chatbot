from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AccessRule:
    selector_type: str
    selector_value: str
    sources: frozenset[str] | None


@dataclass(frozen=True)
class AccessPolicy:
    enabled: bool
    allowed_sources: frozenset[str] | None
    matched_rules: tuple[str, ...] = ()
    reason: str = "unrestricted"

    @property
    def restricted(self) -> bool:
        return self.enabled and self.allowed_sources is not None

    def allows_source(self, source: str | None) -> bool:
        if not self.enabled or self.allowed_sources is None:
            return True
        if not self.allowed_sources:
            return False
        return str(source or "").strip().lower() in self.allowed_sources

    def trace(self) -> dict[str, Any]:
        if self.allowed_sources is None:
            sources: list[str] | str = "all"
        else:
            sources = sorted(self.allowed_sources)

        return {
            "enabled": self.enabled,
            "restricted": self.restricted,
            "allowed_sources": sources,
            "matched_rules": list(self.matched_rules),
            "reason": self.reason,
        }


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _normalize_set(values: Any) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        values = _split_csv(values)
    return {str(value).strip().lower() for value in values if str(value).strip()}


def _parse_sources(raw: str) -> frozenset[str] | None:
    sources = _normalize_set(_split_csv(raw))
    if "*" in sources or "all" in sources:
        return None
    return frozenset(sources)


def _parse_rules(raw_rules: str | None) -> list[AccessRule]:
    rules = []
    for raw_rule in (raw_rules or "").replace("\n", ";").split(";"):
        raw_rule = raw_rule.strip()
        if not raw_rule or "=" not in raw_rule or ":" not in raw_rule:
            continue

        selector, sources = raw_rule.split("=", 1)
        selector_type, selector_value = selector.split(":", 1)
        selector_type = selector_type.strip().lower()
        selector_value = selector_value.strip().lower()
        if not selector_type or not selector_value:
            continue

        rules.append(
            AccessRule(
                selector_type=selector_type,
                selector_value=selector_value,
                sources=_parse_sources(sources),
            )
        )
    return rules


def _user_domain(email: str) -> str:
    return email.rsplit("@", 1)[-1] if "@" in email else ""


def _rule_matches(rule: AccessRule, user: dict[str, Any]) -> bool:
    email = str(user.get("email") or user.get("username") or "").strip().lower()
    user_id = str(user.get("user_id") or user.get("id") or "").strip().lower()
    roles = _normalize_set(user.get("roles") or [])
    groups = _normalize_set(user.get("groups") or [])

    if rule.selector_type in {"*", "all"}:
        return True
    if rule.selector_type == "email":
        return email == rule.selector_value
    if rule.selector_type == "domain":
        return _user_domain(email) == rule.selector_value
    if rule.selector_type in {"user", "user_id", "uid"}:
        return user_id == rule.selector_value
    if rule.selector_type == "role":
        return rule.selector_value in roles
    if rule.selector_type == "group":
        return rule.selector_value in groups

    return False


def _format_rule(rule: AccessRule) -> str:
    return f"{rule.selector_type}:{rule.selector_value}"


def build_access_policy(user: dict[str, Any] | None, settings: Any) -> AccessPolicy:
    if not getattr(settings, "data_access_control_enabled", True):
        return AccessPolicy(False, None, reason="disabled")

    rules = _parse_rules(getattr(settings, "data_access_rules", None))
    default_sources = getattr(settings, "data_access_default_sources", None)
    user = user or {}

    allowed_sources: set[str] | None = set()
    matched_rules = []

    for rule in rules:
        if not _rule_matches(rule, user):
            continue

        matched_rules.append(_format_rule(rule))
        if rule.sources is None:
            return AccessPolicy(
                True,
                None,
                matched_rules=tuple(matched_rules),
                reason="matched_all_sources_rule",
            )
        allowed_sources.update(rule.sources)

    if matched_rules:
        return AccessPolicy(
            True,
            frozenset(allowed_sources),
            matched_rules=tuple(matched_rules),
            reason="matched_source_rules",
        )

    if default_sources:
        return AccessPolicy(
            True,
            _parse_sources(default_sources),
            reason="default_sources",
        )

    if rules:
        return AccessPolicy(True, frozenset(), reason="no_matching_rule")

    return AccessPolicy(True, None, reason="no_rules_configured")
