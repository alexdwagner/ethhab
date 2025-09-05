#!/usr/bin/env python3
"""
Tests for PricingService 0x price fallback and config wiring.
Network calls are mocked; DB repo is stubbed.
"""

import os
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Ensure env flags are set before importing modules that read config
os.environ.setdefault('SMART_MONEY_DISABLE_NETWORK', '0')

from config import config


class FakeRepo:
    def __init__(self, cache=None):
        # cache: dict[(token, bucket_iso)] -> price
        self.cache = cache or {}
        self.upserts = []

    def get_cached_token_price(self, token: str, bucket_iso: str):
        return self.cache.get((token, bucket_iso))

    def upsert_token_price(self, token: str, bucket_iso: str, price: float, source: str = ''):
        self.upserts.append((token, bucket_iso, float(price), source))
        # emulate success
        return True


class TestZeroExPricing(unittest.TestCase):
    def setUp(self):
        # Import module under test and inject fake repo
        from src.services import pricing_service as mod
        self.mod = mod
        # Use a fixed timestamp for deterministic bucket
        self.ts_iso = '2024-01-01T12:34:56Z'
        bucket = datetime.fromisoformat('2024-01-01T12:00:00').isoformat() + 'Z'
        self.bucket_iso = bucket
        # Ensure network-enabled for pricing fallback
        config.SMART_MONEY_DISABLE_NETWORK = False
        # Prefer canonical key per repo convention
        config.ZEROX_SWAP_API_KEY = 'test-0x-key'
        # Prepare fake repo and inject before instance creation
        self.repo = FakeRepo()
        self.mod.smart_money_repository = self.repo

        # Fresh instance each test
        self.service = self.mod.PricingService()

    def test_cache_hit_skips_network(self):
        # Arrange: preload cache for ETH
        self.repo.cache[('eth', self.bucket_iso)] = 123.45

        with patch('requests.get') as mock_get:
            # Act
            price = self.service._get_token_price_usd('eth', self.ts_iso)

            # Assert
            self.assertEqual(price, 123.45)
            self.assertFalse(mock_get.called, 'Should not call network on cache hit')

    def test_cache_miss_calls_zeroex_with_api_key(self):
        # Arrange
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {'price': '345.67'}

        with patch('requests.get') as mock_get:
            mock_get.return_value = fake_resp

            # Act
            price = self.service._get_token_price_usd('eth', self.ts_iso)

            # Assert: price returned and cached
            self.assertAlmostEqual(price or 0.0, 345.67, places=4)
            self.assertTrue(self.repo.upserts, 'Expected cache upsert after external fetch')
            token, bucket, p, source = self.repo.upserts[-1]
            self.assertEqual(token, 'eth')
            self.assertEqual(bucket, self.bucket_iso)
            self.assertAlmostEqual(p, 345.67, places=4)
            self.assertEqual(source, '0x')

            # Assert: called 0x price API with header
            self.assertTrue(mock_get.called)
            args, kwargs = mock_get.call_args
            self.assertIn('https://api.0x.org/swap/v1/price', args[0])
            self.assertIn('headers', kwargs)
            self.assertEqual(kwargs['headers'].get('0x-api-key'), 'test-0x-key')
            # ETH is sent as native shorthand
            params = kwargs.get('params', {})
            self.assertEqual(params.get('buyToken'), '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48')  # USDC
            self.assertEqual(params.get('sellToken'), 'ETH')
            self.assertEqual(params.get('sellAmount'), str(10 ** 18))
            self.assertEqual(params.get('chainId'), 1)

    def test_erc20_cache_miss_uses_token_decimals(self):
        # LINK address (18 decimals in token_info)
        link = '0x514910771af9ca656af840dff83e8264ecf986ca'
        fake_resp = MagicMock()
        fake_resp.status_code = 200
        fake_resp.json.return_value = {'price': '12.34'}

        with patch('requests.get') as mock_get:
            mock_get.return_value = fake_resp

            price = self.service._get_token_price_usd(link, self.ts_iso)

            self.assertAlmostEqual(price or 0.0, 12.34, places=3)
            args, kwargs = mock_get.call_args
            params = kwargs.get('params', {})
            self.assertEqual(params.get('sellToken').lower(), link)
            self.assertEqual(params.get('sellAmount'), str(10 ** 18))

    def test_network_disabled_returns_none_on_cache_miss(self):
        # Recreate service with network disabled
        config.SMART_MONEY_DISABLE_NETWORK = True
        self.service = self.mod.PricingService()
        with patch('requests.get') as mock_get:
            price = self.service._get_token_price_usd('eth', self.ts_iso)
            self.assertIsNone(price)
            self.assertFalse(mock_get.called)


if __name__ == '__main__':
    unittest.main()
