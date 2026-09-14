import os
import json

def get_all_evaluation_metrics():
    models_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'saved_models'))
    
    fraud_metrics_path = os.path.join(models_dir, 'fraud_metrics.json')
    pricing_metrics_path = os.path.join(models_dir, 'pricing_metrics.json')

    fraud_metrics = {}
    pricing_metrics = {}

    if os.path.exists(fraud_metrics_path):
        with open(fraud_metrics_path, 'r') as f:
            fraud_metrics = json.load(f)

    if os.path.exists(pricing_metrics_path):
        with open(pricing_metrics_path, 'r') as f:
            pricing_metrics = json.load(f)

    summary = {
        'fraud_model': fraud_metrics,
        'pricing_model': pricing_metrics
    }

    print("=== Consolidated Model Evaluation Summary ===")
    print("\n[FRAUD DETECTION MODEL (XGBoost Classifier)]")
    if fraud_metrics:
        print(f"Accuracy:  {fraud_metrics.get('accuracy', 0):.4f}")
        print(f"Precision: {fraud_metrics.get('precision', 0):.4f}")
        print(f"Recall:    {fraud_metrics.get('recall', 0):.4f}")
        print(f"F1-Score:  {fraud_metrics.get('f1_score', 0):.4f}")
        print(f"ROC-AUC:   {fraud_metrics.get('roc_auc', 0):.4f}")
    else:
        print("No fraud metrics found.")

    print("\n[DYNAMIC PRICING MODEL (XGBoost Regressor)]")
    if pricing_metrics:
        print(f"R² Score:        {pricing_metrics.get('r2_score', 0):.4f}")
        print(f"RMSE:            ${pricing_metrics.get('rmse', 0):,.2f}")
        print(f"MAE:             ${pricing_metrics.get('mae', 0):,.2f}")
        print(f"MAPE:            {pricing_metrics.get('mape', 0):.2f}%")
        print(f"Revenue Uplift:  +{pricing_metrics.get('revenue_uplift_pct', 0):.2f}%")
    else:
        print("No pricing metrics found.")

    return summary

if __name__ == '__main__':
    get_all_evaluation_metrics()
