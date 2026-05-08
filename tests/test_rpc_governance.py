from __future__ import annotations

from devault.grpc.rpc_governance import TokenBucket


def test_token_bucket_allows_burst_then_limits() -> None:
    b = TokenBucket()
    peer = "ipv4:127.0.0.1:1"
    rps, burst = 10.0, 5.0
    ok_count = 0
    for _ in range(5):
        assert b.allow(peer, rps=rps, burst=burst) is True
        ok_count += 1
    # Immediately exhaust burst; next calls should fail until refill
    denied = 0
    for _ in range(20):
        if not b.allow(peer, rps=rps, burst=burst):
            denied += 1
    assert denied >= 1
