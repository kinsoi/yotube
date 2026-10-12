from app.events import EventBroker


async def test_subscribers_receive_published_events() -> None:
    broker = EventBroker()
    async with broker.subscribe() as first, broker.subscribe() as second:
        broker.publish({"type": "playlist_updated", "playlist_id": 1})
        assert await first.get() == {"type": "playlist_updated", "playlist_id": 1}
        assert await second.get() == {"type": "playlist_updated", "playlist_id": 1}


async def test_unsubscribed_queues_stop_receiving() -> None:
    broker = EventBroker()
    async with broker.subscribe() as queue:
        pass
    broker.publish({"type": "x"})
    assert queue.empty()


async def test_slow_subscribers_drop_events_instead_of_blocking() -> None:
    broker = EventBroker(max_queue=2)
    async with broker.subscribe() as queue:
        for n in range(5):
            broker.publish({"n": n})
        assert queue.qsize() == 2
