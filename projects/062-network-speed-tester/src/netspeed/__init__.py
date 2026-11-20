"""netspeed: a small client/server tool for measuring latency, jitter,
throughput and packet loss between machines you control."""

from .client import SpeedClient, ThroughputResult, UDPResult, udp_probe
from .server import SpeedServer
from .stats import LatencySummary

__all__ = ["SpeedClient", "SpeedServer", "ThroughputResult", "UDPResult", "LatencySummary", "udp_probe"]
__version__ = "1.0.0"
