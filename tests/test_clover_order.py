# test_clover_order.py
import pytest
from datetime import datetime
import pytz
from pages.analysis_folfol_import_sales import CloverOrder, DeliveryInfo


@pytest.fixture
def sample_order_data():
    return {
        "href": "https://www.clover.com/v3/merchants/W5GQK2VX0S921/orders/3H1FAC05323HJ",
        "id": "3H1FAC05323HJ",
        "currency": "CAD",
        "employee": {
            "id": "8HCG02H8R232J"
        },
        "total": 0,
        "paymentState": "PAID",
        "note": "Julien L \n DOORDASH \n DELIVERY 18:37 #MEVFIN-0000042b",
        "orderType": {
            "id": "R38STSGRPQ5SC"
        },
        "taxRemoved": False,
        "isVat": False,
        "state": "locked",
        "manualTransaction": False,
        "groupLineItems": True,
        "testMode": False,
        "payType": "FULL",
        "createdTime": 1733020838000,
        "clientCreatedTime": 1733020838000,
        "modifiedTime": 1733021000000,
        "lineItems": {
            "elements": [
                {
                    "id": "Q3ZE35CVXQ0A4",
                    "orderRef": {
                        "id": "3H1FAC05323HJ"
                    },
                    "item": {
                        "id": "TV5SHN25DGVDW"
                    },
                    "name": "Extra Shish Taouk ",
                    "alternateName": "Side Shish Taouk ",
                    "price": 1300,
                    "itemCode": "TV5SHN25DGVDW",
                    "printed": True,
                    "createdTime": 1733020996000,
                    "orderClientCreatedTime": 1733020838000,
                    "exchanged": False,
                    "modifications": {
                        "elements": [
                            {
                                "id": "2ZFARFJJRTCX8",
                                "lineItemRef": {
                                    "id": "Q3ZE35CVXQ0A4"
                                },
                                "name": "Mélasse / Molasses",
                                "amount": 0,
                                "modifier": {
                                    "id": "F5CQXGXRABPG8"
                                }
                            },
                            {
                                "id": "ESGVGQ0KJ2JGA",
                                "lineItemRef": {
                                    "id": "Q3ZE35CVXQ0A4"
                                },
                                "name": "Cornichons / Pickles",
                                "amount": 0,
                                "modifier": {
                                    "id": "2ZVZDYBHPVFNG"
                                }
                            },
                            {
                                "id": "BR5JDERK87WS6",
                                "lineItemRef": {
                                    "id": "Q3ZE35CVXQ0A4"
                                },
                                "name": "Mayo à l’ail /  Garlic mayo",
                                "amount": 0,
                                "modifier": {
                                    "id": "9BNZNDYZT46XT"
                                }
                            },
                            {
                                "id": "F971JFSEXPAYW",
                                "lineItemRef": {
                                    "id": "Q3ZE35CVXQ0A4"
                                },
                                "name": "Sauce piquante / Hot sauce",
                                "alternateName": "Add Hot Sauce",
                                "amount": 50,
                                "modifier": {
                                    "id": "G1NRBSV2MMZST"
                                }
                            },
                            {
                                "id": "8T33RAV9BPSKT",
                                "lineItemRef": {
                                    "id": "Q3ZE35CVXQ0A4"
                                },
                                "name": "Hummus",
                                "alternateName": "Add Hummus",
                                "amount": 100,
                                "modifier": {
                                    "id": "7RWFHFQMKT5DC"
                                }
                            }
                        ]
                    },
                    "refunded": False,
                    "isRevenue": True,
                    "isOrderFee": False
                }
            ]
        },
        "payments": {
            "elements": [
                {
                    "id": "NTVNBR756R1A8",
                    "order": {
                        "id": "3H1FAC05323HJ"
                    },
                    "device": {
                        "id": "0000042b-d4a4-68f3-a304-b299254dec2e"
                    },
                    "tender": {
                        "href": "https://www.clover.com/v3/merchants/W5GQK2VX0S921/tenders/9JWSGS5T92ZYW",
                        "id": "9JWSGS5T92ZYW"
                    },
                    "amount": 0,
                    "taxAmount": 0,
                    "cashbackAmount": 0,
                    "cashTendered": 0,
                    "employee": {
                        "id": "8HCG02H8R232J"
                    },
                    "createdTime": 1733020999000,
                    "clientCreatedTime": 1733020998000,
                    "modifiedTime": 1733020998000,
                    "result": "SUCCESS"
                }
            ]
        },
        "device": {
            "id": "0000042b-d4a4-68f3-a304-b299254dec2e"
        },

        "discounts": {
            "elements": [
                {
                    "id": "N8NECN3D6CWV2",
                    "orderRef": {
                        "id": "3H1FAC05323HJ"
                    },
                    "discount": {
                        "id": "4VBVXSCG80MFC"
                    },
                    "name": "Staff Discount",
                    "percentage": 100,
                    "discType": "DEFAULT"
                }
            ]
        },
        'detailed_line_items': [
            {
                "id": "Q3ZE35CVXQ0A4",
                "orderRef": {
                    "id": "3H1FAC05323HJ"
                },
                "item": {
                    "id": "TV5SHN25DGVDW"
                },
                "name": "Extra Shish Taouk ",
                "alternateName": "Side Shish Taouk ",
                "price": 1300,
                "itemCode": "TV5SHN25DGVDW",
                "printed": True,
                "createdTime": 1733020996000,
                "orderClientCreatedTime": 1733020838000,
                "discounts": {
                    "elements": [
                        {
                            "id": "0QT592895E0K0",
                            "orderRef": {
                                "id": "3H1FAC05323HJ"
                            },
                            "lineItemRef": {
                                "id": "Q3ZE35CVXQ0A4"
                            },
                            "discount": {
                                "id": "4VBVXSCG80MFC"
                            },
                            "name": "Waste",
                            "amount": 500,
                            "discType": "DEFAULT"
                        }
                    ]
                },
                "exchanged": False,
                "modifications": {
                    "elements": [
                        {
                            "id": "2ZFARFJJRTCX8",
                            "lineItemRef": {
                                "id": "Q3ZE35CVXQ0A4"
                            },
                            "name": "Mélasse / Molasses",
                            "amount": 0,
                            "modifier": {
                                "id": "F5CQXGXRABPG8"
                            }
                        },
                        {
                            "id": "ESGVGQ0KJ2JGA",
                            "lineItemRef": {
                                "id": "Q3ZE35CVXQ0A4"
                            },
                            "name": "Cornichons / Pickles",
                            "amount": 0,
                            "modifier": {
                                "id": "2ZVZDYBHPVFNG"
                            }
                        },
                        {
                            "id": "BR5JDERK87WS6",
                            "lineItemRef": {
                                "id": "Q3ZE35CVXQ0A4"
                            },
                            "name": "Mayo à l’ail /  Garlic mayo",
                            "amount": 0,
                            "modifier": {
                                "id": "9BNZNDYZT46XT"
                            }
                        },
                        {
                            "id": "F971JFSEXPAYW",
                            "lineItemRef": {
                                "id": "Q3ZE35CVXQ0A4"
                            },
                            "name": "Sauce piquante / Hot sauce",
                            "alternateName": "Add Hot Sauce",
                            "amount": 50,
                            "modifier": {
                                "id": "G1NRBSV2MMZST"
                            }
                        },
                        {
                            "id": "8T33RAV9BPSKT",
                            "lineItemRef": {
                                "id": "Q3ZE35CVXQ0A4"
                            },
                            "name": "Hummus",
                            "alternateName": "Add Hummus",
                            "amount": 100,
                            "modifier": {
                                "id": "7RWFHFQMKT5DC"
                            }
                        }
                    ]
                },
                "refunded": False,
                "isRevenue": True,
                "isOrderFee": False
            }
        ]
    }


class TestCloverOrder:
    def test_delivery_info_parsing(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        platform, method, time = DeliveryInfo.parse_delivery_info(order.order_data['note'])

        assert platform == 'Doordash'
        assert method == 'Delivery'
        assert time == '18:37'

    def test_order_details(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        order_details = order.get_order_details()

        # Test each element from get_order_details tuple
        assert order_details[0] == "3H1FAC05323HJ"  # order_id
        assert order_details[1] == "2024-11-30 21:40:38"  # created_time
        assert order_details[2] == "Julien L \n DOORDASH \n DELIVERY 18:37 #MEVFIN-0000042b"  # delivery_note
        assert order_details[6] == "CAD"  # currency
        assert order_details[7] == 0.00  # total (converted from cents to dollars)

    def test_order_level_discount_percentage(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        name, percentage, amount = order.get_order_level_discount()

        assert name == 'Staff Discount'
        assert percentage == 100.0
        assert amount == 0.0

    def test_item_price_with_modifications(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        items = order.get_items()

        assert len(items) == 1
        item = items[0]

        # Check base price and price with modifications
        assert item[3] == 13.0  # Base price
        assert item[4] == 14.50  # Price with modifications ($10 + $2)

    def test_item_final_price_with_discount(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        items = order.get_items()

        assert len(items) == 1
        item = items[0]

        # Check final price after discount
        assert item[0] == 'Q3ZE35CVXQ0A4'
        assert item[2] == 'Extra Shish Taouk '
        assert item[4] == 14.50  # Price with modifications
        assert item[5] == 9.50  # Final price after $5.0 discount

    def test_process_item_discount(self, sample_order_data):
        """
        Test the _process_item_discount method of CloverOrder class.
        This test verifies that the method correctly processes item-level discounts,
        including calculating the final price after discounts.
        """
        # Arrange
        order = CloverOrder(sample_order_data)
        detailed_item = sample_order_data['detailed_line_items'][0]
        price_with_mod = 14.50  # Base price (13.00) + modifications (1.50)

        # Act
        final_price, discount_name, discount_percentage, discount_amount = order._process_item_discount(
            detailed_item,
            price_with_mod
        )

        # Assert
        assert discount_name == 'Waste', f"Expected discount name 'Waste', but got '{discount_name}'"
        assert discount_percentage == 0.0, f"Expected discount percentage 0.0, but got {discount_percentage}"
        assert discount_amount == 5.00, f"Expected discount amount $5.00, but got ${discount_amount}"
        assert final_price == 9.50, f"Expected final price $9.50, but got ${final_price}"

        # Additional assertions to verify the discount details
        discount_element = detailed_item['discounts']['elements'][0]
        assert discount_element['name'] == discount_name, "Discount name should match the source data"
        assert discount_element['amount'] == 500, "Raw discount amount should be 500 cents in source data"

    def test_modifications_extraction(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        mods = order.get_modifications()

        assert len(mods) == 5
        mod = mods[0]

        assert mod[0] == 'Q3ZE35CVXQ0A4'
        assert mod[1] == 'Mélasse / Molasses'
        assert mod[2] == 0.0

        mod = mods[1]

        assert mod[0] == 'Q3ZE35CVXQ0A4'
        assert mod[1] == 'Cornichons / Pickles'
        assert mod[2] == 0.0

        mod = mods[2]

        assert mod[0] == 'Q3ZE35CVXQ0A4'
        assert mod[1] == 'Mayo à l’ail /  Garlic mayo'
        assert mod[2] == 0.0

        mod = mods[3]

        assert mod[0] == 'Q3ZE35CVXQ0A4'
        assert mod[1] == 'Sauce piquante / Hot sauce'
        assert mod[2] == 0.50

        mod = mods[4]

        assert mod[0] == 'Q3ZE35CVXQ0A4'
        assert mod[1] == 'Hummus'
        assert mod[2] == 1.00