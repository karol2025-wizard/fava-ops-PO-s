import pytest
from unittest.mock import MagicMock, patch
from shared.database_operations import DatabaseOperations
from datetime import datetime


@pytest.fixture
def mock_db_manager():
    with patch('shared.database_manager.DatabaseManager') as mock:
        yield mock


@pytest.fixture
def db_ops(mock_db_manager):
    return DatabaseOperations()


class TestDatabaseOperations:
    def test_get_latest_order_date(self, db_ops, mock_db_manager):
        expected_date = datetime(2024, 1, 1)
        mock_db_manager.fetch_one.return_value = (expected_date,)

        result = db_ops.get_latest_order_date()
        assert result == expected_date

    def test_save_orders_batch_processing(self, db_ops, mock_db_manager):
        mock_orders = [
            MagicMock(
                get_order_details=lambda: (
                'ORDER1', '2024-01-01', '', 'In-Store', 'Pickup', None, 'CAD', 25.0, '', '', '', 0, 0),
                get_items=lambda: [('ITEM1', 'ORDER1', 'Burger', 10.0, 12.0, 11.0, '', 0, 0, 'SKU1', 'BURG01', '')],
                get_modifications=lambda: [('ITEM1', 'Extra Cheese', 2.0)],
                get_payments=lambda: [('ORDER1', 2.0, 1.25)]
            )
        ]

        db_ops.save_orders(mock_orders)

        # Verify batch insertions were called
        assert mock_db_manager.execute_batch_insert.call_count >= 4