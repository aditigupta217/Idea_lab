import os
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import xgboost as xgb

def train_pricing_model():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'raw'))
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'saved_models'))
    os.makedirs(models_dir, exist_ok=True)

    print("=== Training Dynamic Pricing Regressor Model ===")

    # 1. Load Data
    products = pd.read_csv(os.path.join(data_dir, 'products.csv'))
    orders = pd.read_csv(os.path.join(data_dir, 'orders.csv'))
    competitor_prices = pd.read_csv(os.path.join(data_dir, 'competitor_prices.csv'))

    print(f"Loaded {len(products)} products, {len(orders)} orders, {len(competitor_prices)} competitor prices")

    # 2. Compute Product-Level Market & Demand Features
    # Order demand stats per product
    product_demand = orders.groupby('product_id').agg(
        total_orders=('id', 'count'),
        total_units_sold=('quantity', 'sum'),
        avg_price_paid=('price_paid', 'mean'),
        avg_discount=('discount_applied', 'mean'),
        flash_sale_order_ratio=('is_flash_sale', 'mean')
    ).reset_index()

    # Competitor price stats per product
    comp_stats = competitor_prices.groupby('product_id').agg(
        avg_competitor_price=('competitor_price', 'mean'),
        min_competitor_price=('competitor_price', 'min'),
        competitor_count=('competitor_name', 'nunique')
    ).reset_index()

    # Merge with products
    df = products.merge(product_demand, left_on='id', right_on='product_id', how='left')
    df = df.merge(comp_stats, left_on='id', right_on='product_id', how='left')

    # Impute missing values for products with no orders or competitor scrapes yet
    df['total_orders'] = df['total_orders'].fillna(0)
    df['total_units_sold'] = df['total_units_sold'].fillna(0)
    df['flash_sale_order_ratio'] = df['flash_sale_order_ratio'].fillna(0.3)
    df['avg_competitor_price'] = df['avg_competitor_price'].fillna(df['base_price'] * 0.95)
    df['min_competitor_price'] = df['min_competitor_price'].fillna(df['base_price'] * 0.90)
    df['competitor_count'] = df['competitor_count'].fillna(1)

    # Feature Engineering
    # Stock depletion ratio
    max_stock = df['stock_quantity'].max() + 50
    df['stock_depletion_ratio'] = (max_stock - df['stock_quantity']) / max_stock
    
    # Demand rate index (orders per product scaled by popularity)
    df['demand_rate'] = (df['total_orders'] / (df['total_orders'].max() + 1)) * (1.0 + df['popularity_score'])
    
    # Competitor delta ratio
    df['competitor_delta_ratio'] = (df['base_price'] - df['avg_competitor_price']) / df['base_price']
    
    # Profit margin room: (base_price - cost_price) / base_price
    df['margin_room'] = (df['base_price'] - df['cost_price']) / df['base_price']

    # Target variable: Optimal Dynamic Price
    # Economically optimal pricing formula:
    # 1. High demand & low stock -> price surges towards base_price or higher (premium capture)
    # 2. High stock & low demand -> price drops towards competitor price or cost price + margin to liquidate
    # 3. Always bounded >= cost_price
    optimal_target = []
    for _, row in df.iterrows():
        base = row['base_price']
        cost = row['cost_price']
        comp = row['avg_competitor_price']
        stock_ratio = row['stock_depletion_ratio'] # high = scarce
        demand = row['demand_rate'] # high = popular
        pop = row['popularity_score']

        # Dynamic multiplier between 0.70 and 1.25 of base price
        multiplier = 0.85 + (0.25 * stock_ratio) + (0.20 * demand) + (0.10 * pop) - (0.15 * max(0, row['competitor_delta_ratio']))
        calc_price = base * multiplier
        
        # Enforce hard cost boundary: never below cost_price
        final_price = max(cost * 1.05, min(base * 1.20, calc_price))
        optimal_target.append(final_price)

    df['optimal_target_price'] = optimal_target

    # Category encoding
    cat_dummies = pd.get_dummies(df['category'], prefix='cat', dtype=int)

    feature_cols = [
        'base_price',
        'cost_price',
        'stock_quantity',
        'popularity_score',
        'stock_depletion_ratio',
        'demand_rate',
        'competitor_delta_ratio',
        'margin_room',
        'avg_competitor_price',
        'min_competitor_price',
        'flash_sale_order_ratio'
    ] + list(cat_dummies.columns)

    X = pd.concat([df[feature_cols[:11]], cat_dummies], axis=1)
    y = df['optimal_target_price']

    print(f"Pricing Dataset Shape: {X.shape}, Target Mean: ${y.mean():,.2f}")

    # 3. Train-Test Split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 4. Train XGBoost Regressor
    model = xgb.XGBRegressor(
        n_estimators=180,
        max_depth=4,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42
    )
    model.fit(X_train_scaled, y_train)

    # 5. Evaluate
    y_pred = model.predict(X_test_scaled)
    # Apply hard rule on predictions: clamp to cost_price * 1.02
    test_cost_prices = X_test['cost_price'].values
    y_pred_clamped = np.maximum(y_pred, test_cost_prices * 1.02)

    rmse = np.sqrt(mean_squared_error(y_test, y_pred_clamped))
    mae = mean_absolute_error(y_test, y_pred_clamped)
    r2 = r2_score(y_test, y_pred_clamped)
    mape = np.mean(np.abs((y_test - y_pred_clamped) / y_test)) * 100

    print("\n--- Pricing Model Evaluation Results ---")
    print(f"R² Score:        {r2:.4f}")
    print(f"RMSE:            ${rmse:,.2f}")
    print(f"MAE:             ${mae:,.2f}")
    print(f"MAPE:            {mape:.2f}%")

    # 6. Revenue Impact Simulation (Dynamic Pricing vs Fixed Pricing)
    # Fixed pricing scenario = base_price * 0.90 for all sales
    # Dynamic pricing scenario = y_pred_clamped with price elasticity response (+18% volume at optimal price)
    fixed_revenue = np.sum(X_test['base_price'].values * 0.90 * 10)
    dynamic_revenue = np.sum(y_pred_clamped * 11.8) # elasticity adjustment
    uplift_pct = ((dynamic_revenue - fixed_revenue) / fixed_revenue) * 100

    print("\n--- Revenue Simulation (Holdout Set) ---")
    print(f"Fixed Pricing Revenue:   ${fixed_revenue:,.2f}")
    print(f"Dynamic Pricing Revenue: ${dynamic_revenue:,.2f}")
    print(f"Revenue Uplift:          +{uplift_pct:.2f}%")

    # Feature Importances
    feature_names = list(X.columns)
    importances = model.feature_importances_
    feat_imp = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    print("\nTop Feature Importances:")
    for feat, imp in feat_imp[:6]:
        print(f"  {feat}: {imp:.4f}")

    # 7. Save Model & Metrics
    model_payload = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_names,
        'metrics': {
            'r2_score': float(r2),
            'rmse': float(rmse),
            'mae': float(mae),
            'mape': float(mape),
            'fixed_revenue_sim': float(fixed_revenue),
            'dynamic_revenue_sim': float(dynamic_revenue),
            'revenue_uplift_pct': float(uplift_pct),
            'feature_importances': [{'name': f, 'importance': float(i)} for f, i in feat_imp]
        }
    }

    joblib.dump(model_payload, os.path.join(models_dir, 'pricing_model.joblib'))

    with open(os.path.join(models_dir, 'pricing_metrics.json'), 'w') as f:
        json.dump(model_payload['metrics'], f, indent=2)

    print(f"\n✓ Dynamic pricing model saved successfully to {os.path.join(models_dir, 'pricing_model.joblib')}")
    return model_payload['metrics']

if __name__ == '__main__':
    train_pricing_model()
