import os
import json
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
import xgboost as xgb

def train_fraud_model():
    data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data', 'raw'))
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'saved_models'))
    os.makedirs(models_dir, exist_ok=True)

    print("=== Training Fraud Detection Model ===")
    
    # 1. Load Data
    customers = pd.read_csv(os.path.join(data_dir, 'customers.csv'))
    orders = pd.read_csv(os.path.join(data_dir, 'orders.csv'))
    fraud_labels = pd.read_csv(os.path.join(data_dir, 'fraud_labels.csv'))

    print(f"Loaded {len(customers)} customers, {len(orders)} orders, {len(fraud_labels)} fraud labels")

    # 2. Merge Data
    df = orders.merge(customers, left_on='customer_id', right_on='id', suffixes=('', '_cust'))
    df = df.merge(fraud_labels[['order_id', 'is_fraud', 'fraud_type']], left_on='id', right_on='order_id', how='inner')

    # 3. Feature Engineering
    # Convert timestamps
    df['order_timestamp_dt'] = pd.to_datetime(df['order_timestamp'])
    df['signup_date_dt'] = pd.to_datetime(df['signup_date'])
    df = df.sort_values('order_timestamp_dt').reset_index(drop=True)

    # Time between account creation and order (in days)
    df['days_since_signup'] = (df['order_timestamp_dt'] - df['signup_date_dt']).dt.total_seconds() / 86400.0
    df['days_since_signup'] = df['days_since_signup'].clip(lower=0)

    # Orders per minute from same IP & Device (rolling 60 second window)
    df['orders_last_min_ip'] = 1
    df['orders_last_min_device'] = 1
    
    # Efficient rolling calculation per IP & device
    for col, new_col in [('ip_address', 'orders_last_min_ip'), ('device_id', 'orders_last_min_device')]:
        counts = []
        for key, group in df.groupby(col):
            times = group['order_timestamp_dt'].values
            for i, t in enumerate(times):
                # Count orders within 60s window up to current order
                window_start = t - np.timedelta64(60, 's')
                c = np.sum((times >= window_start) & (times <= t))
                counts.append((group.index[i], c))
        counts_df = pd.DataFrame(counts, columns=['idx', new_col]).set_index('idx')
        df[new_col] = counts_df[new_col]

    # Coupon reuse frequency
    coupon_counts = df['coupon_code'].value_counts().to_dict()
    df['coupon_reuse_count'] = df['coupon_code'].map(lambda x: coupon_counts.get(x, 0) if pd.notna(x) else 0)

    # Order timing regularity (diff between successive orders for same customer in minutes)
    df['prev_order_time'] = df.groupby('customer_id')['order_timestamp_dt'].shift(1)
    df['time_since_prev_order_mins'] = (df['order_timestamp_dt'] - df['prev_order_time']).dt.total_seconds() / 60.0
    df['time_since_prev_order_mins'] = df['time_since_prev_order_mins'].fillna(9999.0).clip(upper=9999.0)

    # Numeric & Categorical features
    df['is_flash_sale_int'] = df['is_flash_sale'].astype(int)
    df['has_coupon'] = df['coupon_code'].notna().astype(int)
    
    # Payment method one-hot encoding
    payment_dummies = pd.get_dummies(df['payment_method'], prefix='pay', dtype=int)
    
    feature_cols = [
        'account_age_days',
        'days_since_signup',
        'orders_last_min_ip',
        'orders_last_min_device',
        'coupon_reuse_count',
        'time_since_prev_order_mins',
        'quantity',
        'price_paid',
        'discount_applied',
        'is_flash_sale_int',
        'has_coupon'
    ] + list(payment_dummies.columns)

    X = pd.concat([df[feature_cols[:11]], payment_dummies], axis=1)
    y = df['is_fraud'].astype(int)

    print(f"Dataset shape: {X.shape}, Class distribution: Fraud={y.sum()} ({y.mean()*100:.2f}%), Non-Fraud={len(y)-y.sum()}")

    # 4. Train-Test Split (80/20 stratified)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Scaler for numeric columns
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Calculate class weight ratio for imbalance
    scale_pos_weight = (len(y_train) - sum(y_train)) / max(1, sum(y_train))

    # 5. Model Training (XGBoost Classifier)
    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.08,
        scale_pos_weight=scale_pos_weight,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        eval_metric='logloss'
    )
    model.fit(X_train_scaled, y_train)

    # 6. Evaluation
    y_pred = model.predict(X_test_scaled)
    y_prob = model.predict_proba(X_test_scaled)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    roc_auc = roc_auc_score(y_test, y_prob)
    cm = confusion_matrix(y_test, y_pred)

    print("\n--- Model Evaluation Results ---")
    print(f"Accuracy:        {acc:.4f}")
    print(f"Precision:       {prec:.4f}")
    print(f"Recall:          {rec:.4f}")
    print(f"F1 Score:        {f1:.4f}")
    print(f"ROC-AUC Score:   {roc_auc:.4f}")
    print("\nConfusion Matrix:")
    print(f"TN: {cm[0][0]}, FP: {cm[0][1]}")
    print(f"FN: {cm[1][0]}, TP: {cm[1][1]}")
    print("\nClassification Report:\n", classification_report(y_test, y_pred))

    # Feature Importances
    feature_names = list(X.columns)
    importances = model.feature_importances_
    feat_imp = sorted(zip(feature_names, importances), key=lambda x: x[1], reverse=True)
    print("Top Feature Importances:")
    for feat, imp in feat_imp[:6]:
        print(f"  {feat}: {imp:.4f}")

    # 7. Save Model, Scaler & Metrics
    model_payload = {
        'model': model,
        'scaler': scaler,
        'feature_names': feature_names,
        'metrics': {
            'accuracy': float(acc),
            'precision': float(prec),
            'recall': float(rec),
            'f1_score': float(f1),
            'roc_auc': float(roc_auc),
            'confusion_matrix': cm.tolist(),
            'feature_importances': [{'name': f, 'importance': float(i)} for f, i in feat_imp]
        }
    }

    joblib.dump(model_payload, os.path.join(models_dir, 'fraud_model.joblib'))
    
    with open(os.path.join(models_dir, 'fraud_metrics.json'), 'w') as f:
        json.dump(model_payload['metrics'], f, indent=2)

    print(f"\n✓ Fraud detection model saved successfully to {os.path.join(models_dir, 'fraud_model.joblib')}")
    return model_payload['metrics']

if __name__ == '__main__':
    train_fraud_model()
