from pathlib import Path

import yaml

from underwriting_agent.domain.policy import UnderwritingPolicy

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH = PROJECT_ROOT / "configs" / "underwriting_policy.yaml"


def load_underwriting_policy(
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> UnderwritingPolicy:
    if not policy_path.exists():
        raise FileNotFoundError(
            f"Underwriting policy file was not found: {policy_path}"
        )

    with policy_path.open(encoding="utf-8") as file:
        raw_policy: object = yaml.safe_load(file)

    if raw_policy is None:
        raise ValueError(f"Underwriting policy file is empty: {policy_path}")

    return UnderwritingPolicy.model_validate(raw_policy)
