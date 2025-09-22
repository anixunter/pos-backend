customer_purchase_history_response_example = [
    {
        "id": 3,
        "customer": 1,
        "customer_name": "Customer 1",
        "transaction_date": "2025-09-07T04:41:22.933317Z",
        "payment_method": "Cash",
        "subtotal": "1650.00",
        "discount_amount": "0.00",
        "tax_amount": "0.00",
        "total_amount": "1650.00",
        "amount_paid": "1650.00",
        "change_amount": "0.00",
        "notes": "",
        "items": [
            {
                "id": 3,
                "product": 2,
                "product_name": "Basin",
                "quantity": "1.00",
                "unit_price": "1500.00",
                "discount_amount": "0.00",
                "total_price": "1500.00"
            },
            {
                "id": 4,
                "product": 1,
                "product_name": "Water Tap",
                "quantity": "1.00",
                "unit_price": "150.00",
                "discount_amount": "0.00",
                "total_price": "150.00"
            }
        ],
        "returns": [
            {
                "id": 1,
                "transaction": 3,
                "return_date": "2025-09-07T05:01:32.850793Z",
                "reason": "dont need warter tap",
                "refund_amount": "150.00",
                "refund_method": "Cash",
                "notes": "",
                "items": [
                    {
                        "id": 1,
                        "product": 1,
                        "product_name": "Water Tap",
                        "quantity": "1.00",
                        "unit_price": "150.00",
                        "total_price": "150.00"
                    }
                ]
            }
        ]
    }
]