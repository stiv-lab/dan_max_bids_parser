# path: tests/db/test_repositories_basic_crud.py
from datetime import datetime, timedelta

from dan_max_bids_parser.domain.entities import BidEntity, RawItemEntity, SourceEntity
from dan_max_bids_parser.infrastructure.db.base import SessionFactory
from dan_max_bids_parser.infrastructure.db.repositories import (
    SqlAlchemyBidRepository,
    SqlAlchemyRawItemRepository,
    SqlAlchemySourceRepository,
)


def test_source_repository_basic_crud():
    session = SessionFactory()
    repo = SqlAlchemySourceRepository(session=session)

    try:
        # create
        src = SourceEntity(
            code="TEST_SRC",
            name="Test Source",
            kind="html",
            is_active=True,
            description="Тестовый источник",
        )
        saved = repo.save(src)

        assert saved.id is not None

        # read by id
        loaded_by_id = repo.get_by_id(saved.id or 0)
        assert loaded_by_id is not None
        assert loaded_by_id.code == "TEST_SRC"

        # read by code
        loaded_by_code = repo.get_by_code("TEST_SRC")
        assert loaded_by_code is not None
        assert loaded_by_code.id == saved.id

        # update
        saved.name = "Updated Source Name"
        updated = repo.save(saved)
        assert updated.name == "Updated Source Name"

        again = repo.get_by_id(updated.id or 0)
        assert again is not None
        assert again.name == "Updated Source Name"

        # list_all / list_active
        all_sources = repo.list_all()
        active_sources = repo.list_active()
        assert any(s.code == "TEST_SRC" for s in all_sources)
        assert any(s.code == "TEST_SRC" for s in active_sources)
    finally:
        # без commit данные не сохранятся, но на всякий случай делаем rollback
        session.rollback()
        session.close()


def test_raw_item_repository_and_mapping():
    session = SessionFactory()
    src_repo = SqlAlchemySourceRepository(session=session)
    raw_repo = SqlAlchemyRawItemRepository(session=session)

    try:
        source = src_repo.save(
            SourceEntity(
                code="RAW_TEST",
                name="Raw Test Source",
                kind="html",
                is_active=True,
                description="",
            )
        )

        now = datetime.utcnow()
        raw = RawItemEntity(
            source_id=source.id or 0,
            external_id="ext-1",
            payload="<html>payload</html>",
            url="https://example.com/item/1",
            created_at=now,
            received_at=now,
        )

        saved_raw = raw_repo.add(raw)
        assert saved_raw.id is not None

        loaded = raw_repo.get_by_id(saved_raw.id or 0)
        assert loaded is not None
        assert loaded.source_id == source.id
        assert "payload" in loaded.payload

        since = now - timedelta(days=1)
        items = raw_repo.list_for_source_since(source_id=source.id or 0, since=since)
        assert any(i.id == saved_raw.id for i in items)
    finally:
        session.rollback()
        session.close()


def test_bid_repository_and_duplicates():
    session = SessionFactory()
    src_repo = SqlAlchemySourceRepository(session=session)
    bid_repo = SqlAlchemyBidRepository(session=session)

    try:
        source = src_repo.save(
            SourceEntity(
                code="BID_TEST",
                name="Bid Test Source",
                kind="html",
                is_active=True,
                description="",
            )
        )

        now = datetime.utcnow()
        bid = BidEntity(
            source_id=source.id or 0,
            raw_item_id=None,
            external_id="BID-123",
            title="Перевозка щебня",
            description="Нужна перевозка 30 т щебня",
            cargo_type="щебень",
            transport_type="самосвал",
            load_point="Москва",
            unload_point="СПб",
            weight_tons=30.0,
            price=25000.0,
            currency="RUB",
            contact="+7 900 000-00-00",
            url="https://example.com/bid/123",
            published_at=now,
            created_at=now,
        )

        saved_bid = bid_repo.add(bid)
        assert saved_bid.id is not None

        loaded = bid_repo.get_by_id(saved_bid.id or 0)
        assert loaded is not None
        assert loaded.external_id == "BID-123"
        assert loaded.price == 25000.0

        since = now - timedelta(days=1)
        bids = bid_repo.list_for_source_since(
            source_id=source.id or 0,
            since=since,
        )
        assert any(b.id == saved_bid.id for b in bids)

        dup_candidates = bid_repo.find_duplicates_candidates(saved_bid)
        assert any(b.id == saved_bid.id for b in dup_candidates)
    finally:
        session.rollback()
        session.close()
