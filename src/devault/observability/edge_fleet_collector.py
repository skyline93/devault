"""DB-derived fleet health signals for Prometheus (§十四-13)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY
from sqlalchemy import func, select

from devault.db.models import EdgeAgent
from devault.db.session import SessionLocal
from devault.settings import get_settings

logger = logging.getLogger(__name__)

_registered = False


class EdgeFleetHealthCollector:
    """Counts edge Agents whose last_seen is older than the configured stale window."""

    def collect(self):
        mf = GaugeMetricFamily(
            "devault_edge_agents_stale_count",
            "edge_agents rows whose last_seen_at is older than DEVAULT_FLEET_AGENT_STALE_SECONDS",
            labels=["window"],
        )
        try:
            s = get_settings()
            cutoff = datetime.now(timezone.utc) - timedelta(seconds=s.fleet_agent_stale_seconds)
            with SessionLocal() as db:
                n = int(
                    db.execute(
                        select(func.count()).select_from(EdgeAgent).where(EdgeAgent.last_seen_at < cutoff)
                    ).scalar_one()
                )
            mf.add_metric([str(int(s.fleet_agent_stale_seconds))], float(n))
        except Exception:
            logger.exception("edge fleet health collector query failed")
            mf.add_metric(["unknown"], 0.0)
        yield mf


def register_edge_fleet_health_collector() -> None:
    global _registered
    if _registered:
        return
    REGISTRY.register(EdgeFleetHealthCollector())
    _registered = True
