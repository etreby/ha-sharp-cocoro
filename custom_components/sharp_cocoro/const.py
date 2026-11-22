"""Constants for the Sharp Cocoro Air integration."""

DOMAIN = "sharp_cocoro"

# Sharp runs regional API servers. The upstream ``sharp-cocoro`` library
# hardcodes the global host (``hms.cloudlabs.sharp.co.jp``). An account that
# Sharp has provisioned on a regional server must talk to that region's host,
# otherwise every request comes back ``401 Unauthorized`` (observed 2026-11-16
# when Egyptian accounts were migrated to ``eg-hms``). The ``service_name``
# chosen during setup selects the region.
REGION_API_BASES = {
    "sharp-egy": "https://eg-hms.cloudlabs.sharp.co.jp/hems/pfApi/ta",
}


def apply_region_api_base(cocoro, service_name):
    """Point an already-constructed Cocoro client at its regional API server.

    No-op when the ``service_name`` has no known regional host, so the library
    keeps its default global endpoint.
    """
    base = REGION_API_BASES.get(service_name)
    if base:
        cocoro.api_base = base
    return cocoro
