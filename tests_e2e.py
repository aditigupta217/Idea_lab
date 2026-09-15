import os
import sys
import unittest
from app import create_app
from app.models import db, Product, Customer, Order, FraudAlert, PriceLog

class EndToEndTestSuite(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_01_storefront_catalog_and_detail(self):
        # Home page
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'FlashDeals', response.data)

        # Product detail
        prod = Product.query.first()
        self.assertIsNotNone(prod)
        response = self.client.get(f'/products/{prod.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(prod.name.encode('utf-8')[:15], response.data)

    def test_02_dynamic_pricing_api(self):
        prod = Product.query.first()
        # Fetch recommendations
        response = self.client.get('/api/pricing/recommendations')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(data['count'], 0)

        # Apply recommended price
        rec_price = prod.cost_price * 1.10
        response = self.client.post(f'/api/pricing/apply/{prod.id}', json={'price': rec_price})
        self.assertEqual(response.status_code, 200)
        
        # Verify PriceLog audit entry was recorded
        log = PriceLog.query.filter_by(product_id=prod.id).order_by(PriceLog.timestamp.desc()).first()
        self.assertIsNotNone(log)
        self.assertEqual(round(log.new_price, 2), round(rec_price, 2))

    def test_03_cart_and_checkout_flow(self):
        prod = Product.query.first()
        # Add to cart
        resp = self.client.post('/api/cart/add', json={'product_id': prod.id, 'quantity': 2})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

        # Login customer
        login_resp = self.client.post('/login', data={'email': 'customer@idealab.com', 'password': 'customer123'}, follow_redirects=True)
        self.assertEqual(login_resp.status_code, 200)

        # Process checkout with normal behavior
        checkout_resp = self.client.post('/api/checkout', json={'coupon_code': 'FLASH20', 'payment_method': 'Card', 'simulated_burst': 1})
        self.assertEqual(checkout_resp.status_code, 200)
        chk_data = checkout_resp.get_json()
        self.assertTrue(chk_data['success'])
        self.assertIn(chk_data['decision'], ['APPROVED', 'PENDING_REVIEW'])

    def test_04_fraud_detection_simulation(self):
        # Simulate attack traffic
        resp = self.client.post('/api/fraud/simulate-attack', json={'attack_type': 'bot_burst'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertGreater(data['simulated_attempts'], 0)

        # Check that alerts were recorded
        latest_alert = FraudAlert.query.order_by(FraudAlert.created_at.desc()).first()
        self.assertIsNotNone(latest_alert)
        self.assertIn(latest_alert.decision, ['BLOCKED', 'PENDING_REVIEW'])

        # Test admin decision update
        decision_resp = self.client.post(f'/api/fraud/decision/{latest_alert.id}', json={'decision': 'BLOCKED'})
        self.assertEqual(decision_resp.status_code, 200)
        self.assertTrue(decision_resp.get_json()['success'])

    def test_05_admin_dashboard_views(self):
        # Overview
        resp = self.client.get('/admin/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Flash Shield', resp.data)

        # Pricing View
        resp = self.client.get('/admin/pricing')
        self.assertEqual(resp.status_code, 200)

        # Fraud Alerts View
        resp = self.client.get('/admin/fraud-alerts')
        self.assertEqual(resp.status_code, 200)

        # Orders & Users View
        resp = self.client.get('/admin/orders-users')
        self.assertEqual(resp.status_code, 200)

        # Analytics View
        resp = self.client.get('/admin/analytics')
        self.assertEqual(resp.status_code, 200)

        # Model Performance View
        resp = self.client.get('/admin/model-metrics')
        self.assertEqual(resp.status_code, 200)

        # Reports View & CSV Export
        resp = self.client.get('/admin/reports')
        self.assertEqual(resp.status_code, 200)

        resp = self.client.get('/admin/api/export-csv?type=pricing')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.mimetype, 'text/csv')

if __name__ == '__main__':
    unittest.main()
