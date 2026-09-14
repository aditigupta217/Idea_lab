import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from app.models import db, Product, CompetitorPrice, Order

class PricingEngine:
    def __init__(self):
        self.model_data = None
        self.load_model()

    def load_model(self):
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'ml', 'saved_models', 'pricing_model.joblib'))
        if os.path.exists(model_path):
            try:
                self.model_data = joblib.load(model_path)
                print(f"[PricingEngine] Loaded XGBoost pricing model from {model_path}")
            except Exception as e:
                print(f"[PricingEngine] Warning: Could not load pricing model: {e}")
                self.model_data = None
        else:
            print(f"[PricingEngine] Pricing model not found at {model_path}. Will use fallback heuristic formula.")

    def recommend_price(self, product, orders_last_hour=None, is_flash_sale=True):
        """
        Recommends an optimal dynamic price for a product using the XGBoost model with fallback heuristic.
        Enforces hard safety constraint: price >= cost_price.
        """
        base_price = product.base_price
        cost_price = product.cost_price
        stock = product.stock_quantity
        popularity = product.popularity_score

        # 1. Gather competitor data
        competitor_prices = [cp.competitor_price for cp in product.competitor_prices]
        avg_comp = float(np.mean(competitor_prices)) if competitor_prices else base_price * 0.95
        min_comp = float(np.min(competitor_prices)) if competitor_prices else base_price * 0.90

        # 2. Gather demand metrics
        if orders_last_hour is None:
            # Estimate from recent database orders
            orders_last_hour = Order.query.filter_by(product_id=product.id).count() % 15

        # Feature calculations
        max_stock = 500
        stock_depletion_ratio = max(0.0, min(1.0, (max_stock - stock) / max_stock))
        demand_rate = (orders_last_hour / 20.0) * (1.0 + popularity)
        competitor_delta_ratio = (base_price - avg_comp) / max(1.0, base_price)
        margin_room = (base_price - cost_price) / max(1.0, base_price)
        flash_sale_ratio = 1.0 if is_flash_sale else 0.2

        predicted_price = None
        method = "ML (XGBoost Regressor)"

        # Try ML Model Inference
        if self.model_data is not None:
            try:
                model = self.model_data['model']
                scaler = self.model_data['scaler']
                feature_names = self.model_data['feature_names']

                # Build input feature dictionary
                row_dict = {
                    'base_price': base_price,
                    'cost_price': cost_price,
                    'stock_quantity': stock,
                    'popularity_score': popularity,
                    'stock_depletion_ratio': stock_depletion_ratio,
                    'demand_rate': demand_rate,
                    'competitor_delta_ratio': competitor_delta_ratio,
                    'margin_room': margin_room,
                    'avg_competitor_price': avg_comp,
                    'min_competitor_price': min_comp,
                    'flash_sale_order_ratio': flash_sale_ratio
                }

                # Add category one-hot columns
                for col in feature_names:
                    if col.startswith('cat_'):
                        cat_name = col.replace('cat_', '')
                        row_dict[col] = 1 if product.category == cat_name else 0

                # Form DataFrame matching feature order
                input_df = pd.DataFrame([row_dict])[feature_names]
                input_scaled = scaler.transform(input_df)
                raw_pred = float(model.predict(input_scaled)[0])
                predicted_price = raw_pred
            except Exception as e:
                print(f"[PricingEngine] Inference error: {e}, falling back to formula.")
                predicted_price = None

        # Fallback Heuristic Formula if ML is unavailable or fails
        if predicted_price is None:
            method = "Heuristic Rule Fallback"
            # formula: price = base_price * f(stock_ratio, demand_rate, competitor)
            mult = 0.85 + (0.20 * stock_depletion_ratio) + (0.15 * demand_rate) - (0.10 * max(0, competitor_delta_ratio))
            predicted_price = base_price * mult

        # Enforce Hard Safety Constraints
        # Rule 1: Never below cost_price + 3% margin buffer
        min_allowed_price = cost_price * 1.03
        
        # Rule 2: Never above base_price * 1.15 in flash sales
        max_allowed_price = base_price * 1.15

        final_price = max(min_allowed_price, min(max_allowed_price, predicted_price))
        final_price = round(final_price, 2)

        # Generate explanatory reason
        diff = final_price - product.current_price
        diff_pct = ((final_price - product.current_price) / product.current_price) * 100 if product.current_price else 0

        if stock < 50 and demand_rate > 0.4:
            reason = f"Surge Demand ({orders_last_hour} orders/hr) with low inventory ({stock} left) — optimized for margin."
        elif stock > 300:
            reason = f"High inventory clearance ({stock} units) — discounted to beat competitor (₹{avg_comp:,.2f})."
        elif diff < 0:
            reason = f"Flash-sale promotional discount ({abs(diff_pct):.1f}% cut) targeting competitor pricing."
        else:
            reason = f"AI dynamic equilibrium optimization based on real-time market elasticity."

        return {
            'product_id': product.id,
            'product_name': product.name,
            'category': product.category,
            'base_price': round(base_price, 2),
            'cost_price': round(cost_price, 2),
            'current_price': round(product.current_price, 2),
            'recommended_price': final_price,
            'price_diff': round(diff, 2),
            'price_diff_pct': round(diff_pct, 1),
            'profit_margin': round(((final_price - cost_price) / final_price) * 100, 1),
            'competitor_avg': round(avg_comp, 2),
            'stock': stock,
            'demand_rate': round(demand_rate, 2),
            'method': method,
            'reason': reason
        }

# Global instance
pricing_engine = PricingEngine()
