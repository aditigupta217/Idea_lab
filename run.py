import os
from app import create_app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"================================================================")
    print(f" Dynamic Pricing & Fraud Detection System Starting on port {port}")
    print(f" - Customer Storefront:  http://127.0.0.1:{port}/")
    print(f" - Admin Command Center: http://127.0.0.1:{port}/admin")
    print(f" - Admin Login:          http://127.0.0.1:{port}/admin/login (admin@idealab.com / admin123)")
    print(f" - Customer Login:       http://127.0.0.1:{port}/login (customer@idealab.com / customer123)")
    print(f"================================================================")
    app.run(host='0.0.0.0', port=port, debug=True)
