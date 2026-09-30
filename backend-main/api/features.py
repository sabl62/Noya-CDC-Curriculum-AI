"""Runtime feature switches backed by optional feature modules."""

from importlib import import_module
from pathlib import Path


def billing_enabled() -> bool:
    """Enable Pro only when both optional billing modules are present."""
    project_root = Path(__file__).resolve().parents[2]
    pro_ui = project_root / "frontend" / "src" / "pro"
    required_ui = ("BillingPage.jsx", "ChatProFeatures.jsx", "SettingsPro.jsx")
    if not all((pro_ui / name).is_file() for name in required_ui):
        return False
    api_dir = Path(__file__).resolve().parent
    required_server = ("billing.py", "pro_models.py", "pro_admin.py", "pro_usage.py", "pro_ai.py", "payment_gateways.py")
    if not all((api_dir / name).is_file() for name in required_server):
        return False
    try:
        import_module(".billing", package=__package__)
        return True
    except Exception:
        return False
