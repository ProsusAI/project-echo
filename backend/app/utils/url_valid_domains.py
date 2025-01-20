
from threading import Lock
from typing import Set

from app.utils.resources import Resources

_valid_domains = None
_valid_domains_lock = Lock()


def _import_domains() -> Set[str]:
    txt = Resources.get_resource("iana-domains.list")
    lines = {x.lower() for x in txt.split('\n') if x and x[0] != "#"}
    return lines


def get_valid_domains() -> Set[str]:
    global _valid_domains
    if _valid_domains is None:
        with _valid_domains_lock:
            if _valid_domains is None:
                _valid_domains = _import_domains()
    return _valid_domains


valid_schemes = {
    "http",
    "https",
}
