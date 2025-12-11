# test_clover_order.py
import pytest
from datetime import datetime
import pytz
from pages.sales_data_clover import CloverOrder, DeliveryInfo


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
                            "name": "Staff Discount",
                            "percentage": 100,
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
    def test_delivery_info_parsing(self):
        order = CloverOrder({'note': 'DOORDASH DELIVERY 14:30'})
        platform, method, time = DeliveryInfo.parse_delivery_info(order.order_data['note'])

        assert platform == 'Doordash'
        assert method == 'Delivery'
        assert time == '18:37'

    def test_order_level_discount_percentage(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        name, percentage, amount = order.get_order_level_discount()

        assert name == 'Happy Hour'
        assert percentage == 10.0
        assert amount == 0.0

    def test_order_level_discount_amount(self):
        order_data = {
            'discounts': {
                'elements': [
                    {
                        'name': 'Five Dollars Off',
                        'amount': 500  # $5.00
                    }
                ]
            }
        }
        order = CloverOrder(order_data)
        name, percentage, amount = order.get_order_level_discount()

        assert name == 'Five Dollars Off'
        assert percentage == 0.0
        assert amount == 5.0

    def test_item_price_with_modifications(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        items = order.get_items()

        assert len(items) == 1
        item = items[0]

        # Check base price and price with modifications
        assert item[3] == 10.0  # Base price
        assert item[4] == 12.0  # Price with modifications ($10 + $2)

    def test_item_final_price_with_discount(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        items = order.get_items()

        assert len(items) == 1
        item = items[0]

        # Check final price after discount
        assert item[0] == 'ITEM123'
        assert item[2] == 'Burger'
        assert item[4] == 12.0  # Price with modifications
        assert item[5] == 11.0  # Final price after $1.00 discount

    def test_modifications_extraction(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        mods = order.get_modifications()

        assert len(mods) == 1
        mod = mods[0]

        assert mod[0] == 'ITEM123'
        assert mod[1] == 'Extra Cheese'
        assert mod[2] == 2.0

    def test_timezone_conversion(self, sample_order_data):
        order = CloverOrder(sample_order_data)
        order_details = order.get_order_details()

        # Convert timestamp to EST
        est_tz = pytz.timezone('America/New_York')
        expected_time = datetime.fromtimestamp(1635789600, pytz.utc).astimezone(est_tz)

        assert order_details[1] == expected_time.strftime('%Y-%m-%d %H:%M:%S')
