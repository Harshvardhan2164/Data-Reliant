"""Synthetic enterprise data generator producing relational, distributed datasets."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl


class EnterpriseDataGenerator:
    """Generates synthetic enterprise datasets with configurable distributions and relationships."""

    def __init__(self, seed: int = 42) -> None:
        self.seed = seed
        self.rng = np.random.default_rng(seed)

    def generate_customers(
        self,
        n_rows: int = 1000,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pl.DataFrame:
        """Generate synthetic customer accounts."""
        start = start_date or datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = end_date or datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        total_seconds = int((end - start).total_seconds())

        customer_ids = [f"CUST_{i:06d}" for i in range(1, n_rows + 1)]
        countries = ["US", "DE", "GB", "FR", "CA", "JP", "IN", "AU"]
        country_weights = [0.40, 0.15, 0.12, 0.10, 0.08, 0.05, 0.05, 0.05]
        assigned_countries = self.rng.choice(countries, size=n_rows, p=country_weights)

        segments = ["RETAIL", "SMB", "ENTERPRISE"]
        assigned_segments = self.rng.choice(segments, size=n_rows, p=[0.70, 0.20, 0.10])

        # Account balances drawn from log-normal distribution
        balances = np.round(self.rng.lognormal(mean=7.0, sigma=1.2, size=n_rows), 2)

        # Random creation timestamps
        random_offsets = self.rng.integers(0, max(total_seconds, 1), size=n_rows)
        created_ats = [start + timedelta(seconds=int(s)) for s in random_offsets]

        # Credit scores: normal distribution [300, 850]
        credit_scores = np.clip(
            np.round(self.rng.normal(loc=710.0, scale=60.0, size=n_rows)), 300, 850
        ).astype(int)

        return pl.DataFrame(
            {
                "customer_id": customer_ids,
                "country": assigned_countries,
                "segment": assigned_segments,
                "credit_score": credit_scores,
                "account_balance": balances,
                "created_at": created_ats,
            }
        ).sort("customer_id")

    def generate_products(self, n_rows: int = 200) -> pl.DataFrame:
        """Generate product catalogue with realistic margins."""
        product_ids = [f"PROD_{i:04d}" for i in range(1, n_rows + 1)]
        categories = ["ELECTRONICS", "APPAREL", "HOME", "BOOKS", "SOFTWARE"]
        cat_choices = self.rng.choice(categories, size=n_rows, p=[0.25, 0.30, 0.20, 0.15, 0.10])

        costs = np.round(self.rng.uniform(5.0, 500.0, size=n_rows), 2)
        markups = self.rng.uniform(1.2, 2.5, size=n_rows)
        prices = np.round(costs * markups, 2)
        stocks = self.rng.integers(10, 5000, size=n_rows)

        return pl.DataFrame(
            {
                "product_id": product_ids,
                "category": cat_choices,
                "cost": costs,
                "price": prices,
                "stock_level": stocks,
            }
        )

    def generate_transactions(
        self,
        customers_df: pl.DataFrame,
        products_df: pl.DataFrame,
        n_rows: int = 5000,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> pl.DataFrame:
        """Generate transactions referencing customers and products."""
        start = start_date or datetime(2025, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        end = end_date or datetime(2025, 6, 1, 0, 0, 0, tzinfo=timezone.utc)
        total_seconds = int((end - start).total_seconds())

        tx_ids = [f"TX_{i:08d}" for i in range(1, n_rows + 1)]

        cust_list = customers_df["customer_id"].to_list()
        prod_list = products_df["product_id"].to_list()

        chosen_custs = self.rng.choice(cust_list, size=n_rows)
        chosen_prods = self.rng.choice(prod_list, size=n_rows)

        quantities = self.rng.integers(1, 10, size=n_rows)

        # Price lookup
        price_map = dict(zip(products_df["product_id"].to_list(), products_df["price"].to_list(), strict=False))
        amounts = np.round(
            np.array([price_map[p] for p in chosen_prods]) * quantities, 2
        )

        channels = ["WEB", "MOBILE_APP", "PARTNER_API", "IN_STORE"]
        chosen_channels = self.rng.choice(channels, size=n_rows, p=[0.45, 0.35, 0.10, 0.10])

        random_secs = np.sort(self.rng.integers(0, max(total_seconds, 1), size=n_rows))
        timestamps = [start + timedelta(seconds=int(s)) for s in random_secs]

        return pl.DataFrame(
            {
                "transaction_id": tx_ids,
                "customer_id": chosen_custs,
                "product_id": chosen_prods,
                "quantity": quantities,
                "amount": amounts,
                "channel": chosen_channels,
                "timestamp": timestamps,
            }
        )

    def generate_payments(
        self,
        transactions_df: pl.DataFrame,
    ) -> pl.DataFrame:
        """Generate payment processing records linked to transactions."""
        n_rows = transactions_df.height
        payment_ids = [f"PAY_{i:08d}" for i in range(1, n_rows + 1)]
        tx_ids = transactions_df["transaction_id"].to_list()
        tx_times = transactions_df["timestamp"].to_list()

        methods = ["CREDIT_CARD", "DEBIT_CARD", "WIRE_TRANSFER", "PAYPAL"]
        chosen_methods = self.rng.choice(methods, size=n_rows, p=[0.55, 0.25, 0.10, 0.10])

        # 95% settled, 3% failed, 2% pending
        statuses = self.rng.choice(["SETTLED", "FAILED", "PENDING"], size=n_rows, p=[0.95, 0.03, 0.02])

        # Processing delay between 1 second and 120 seconds
        delays = self.rng.integers(1, 120, size=n_rows)
        processed_ats = [t + timedelta(seconds=int(d)) for t, d in zip(tx_times, delays, strict=False)]

        amounts = transactions_df["amount"].to_numpy()
        fees = np.round(amounts * 0.025 + 0.30, 2)

        return pl.DataFrame(
            {
                "payment_id": payment_ids,
                "transaction_id": tx_ids,
                "method": chosen_methods,
                "amount": amounts,
                "fee": fees,
                "status": statuses,
                "processed_at": processed_ats,
            }
        )

    def generate_full_enterprise_dataset(
        self,
        n_customers: int = 1000,
        n_products: int = 100,
        n_transactions: int = 5000,
        output_dir: Path | str | None = None,
    ) -> dict[str, pl.DataFrame]:
        """Generate and optionally save complete set of linked enterprise datasets."""
        cust_df = self.generate_customers(n_rows=n_customers)
        prod_df = self.generate_products(n_rows=n_products)
        tx_df = self.generate_transactions(cust_df, prod_df, n_rows=n_transactions)
        pay_df = self.generate_payments(tx_df)

        datasets = {
            "customers": cust_df,
            "products": prod_df,
            "transactions": tx_df,
            "payments": pay_df,
        }

        if output_dir:
            out_p = Path(output_dir)
            out_p.mkdir(parents=True, exist_ok=True)
            for name, df in datasets.items():
                df.write_parquet(out_p / f"{name}.parquet")
                df.write_csv(out_p / f"{name}.csv")

        return datasets

    def generate(
        self,
        n_customers: int = 1000,
        n_products: int = 100,
        n_transactions: int = 5000,
        n_payments: int | None = None,
        output_dir: Path | str | None = None,
    ) -> dict[str, pl.DataFrame]:
        """Convenience alias for generate_full_enterprise_dataset."""
        return self.generate_full_enterprise_dataset(
            n_customers=n_customers,
            n_products=n_products,
            n_transactions=n_transactions,
            output_dir=output_dir,
        )
