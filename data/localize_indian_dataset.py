import os
import pandas as pd
import numpy as np
import random

def localize_data():
    raw_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'raw'))
    
    print("=== Localizing Dataset to Indian Context ===")

    # 1. Indian Names & Email Pools
    first_names = [
        "Aarav", "Aditi", "Priya", "Rahul", "Rohit", "Ananya", "Vikram", "Sneha", "Aditya", "Neha",
        "Rohan", "Pooja", "Arjun", "Kavya", "Siddharth", "Ishita", "Varun", "Tanvi", "Amit", "Riya",
        "Karan", "Shreya", "Deepak", "Meera", "Manish", "Divya", "Suresh", "Ritu", "Gaurav", "Simran",
        "Rajesh", "Swati", "Nikhil", "Akanksha", "Harsh", "Pallavi", "Vivek", "Anjali", "Alok", "Preeti",
        "Sameer", "Komal", "Abhishek", "Poonam", "Mayank", "Nisha", "Sunil", "Payal", "Pranav", "Rashmi"
    ]
    last_names = [
        "Sharma", "Verma", "Patel", "Gupta", "Mehta", "Singh", "Roy", "Iyer", "Nair", "Kapoor",
        "Reddy", "Chopra", "Joshi", "Bhatia", "Deshmukh", "Agarwal", "Bose", "Saxena", "Malhotra", "Kulkarni",
        "Banerjee", "Pandey", "Chatterjee", "Mishra", "Trivedi", "Dutta", "Goswami", "Shukla", "Pillai", "Menon",
        "Kumar", "Yadav", "Chauhan", "Bhatt", "Sengupta", "Rao", "Shetty", "Das", "Ghosh", "Mukherjee"
    ]
    domains = ["gmail.com", "yahoo.in", "outlook.com", "rediffmail.com", "icloud.com"]

    # --- Update customers.csv ---
    cust_path = os.path.join(raw_dir, 'customers.csv')
    df_cust = pd.read_csv(cust_path)
    
    random.seed(42)
    np.random.seed(42)

    new_names = []
    new_emails = []
    used_emails = set()

    for i in range(len(df_cust)):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        full_name = f"{fn} {ln}"
        
        # Unique email
        base_email = f"{fn.lower()}.{ln.lower()}{random.randint(10, 999)}@{random.choice(domains)}"
        while base_email in used_emails:
            base_email = f"{fn.lower()}{random.randint(100, 9999)}@{random.choice(domains)}"
        used_emails.add(base_email)
        
        new_names.append(full_name)
        new_emails.append(base_email)

    df_cust['name'] = new_names
    df_cust['email'] = new_emails
    df_cust.to_csv(cust_path, index=False)
    print(f"✓ Updated {len(df_cust)} customers with Indian names and emails.")

    # --- Update products.csv with Indian E-Commerce Products ---
    prod_path = os.path.join(raw_dir, 'products.csv')
    df_prod = pd.read_csv(prod_path)

    indian_product_catalog = [
        # Electronics
        ("OnePlus Nord CE4 5G Smartphone (128GB)", "Electronics", 24999.0, 19500.0, 22999.0),
        ("boAt Rockerz 450 Bluetooth Wireless Headphones", "Electronics", 2990.0, 950.0, 1499.0),
        ("Samsung 43-inch Crystal 4K UHD Smart TV", "Electronics", 39990.0, 26000.0, 29990.0),
        ("Noise ColorFit Pulse 3 Smartwatch (Bluetooth Calling)", "Electronics", 4999.0, 1100.0, 1699.0),
        ("Mi Power Bank 3i 20000mAh Fast Charging (18W)", "Electronics", 2199.0, 1200.0, 1799.0),
        ("HP 15s Intel Core i5 12th Gen Laptop (16GB/512GB SSD)", "Electronics", 58990.0, 44000.0, 49990.0),
        ("Realme Buds Air 5 ANC True Wireless Earbuds", "Electronics", 4999.0, 2200.0, 3299.0),
        ("SanDisk Ultra 128GB MicroSDXC Memory Card", "Electronics", 1800.0, 650.0, 899.0),
        ("Zebronics 2.1 Channel Bluetooth Soundbar with Subwoofer", "Electronics", 6999.0, 2800.0, 3999.0),
        ("Logitech B170 Wireless Optical Mouse", "Electronics", 895.0, 420.0, 599.0),
        ("Fire-Boltt Ninja Call Pro Plus 1.83 Smartwatch", "Electronics", 7999.0, 999.0, 1299.0),
        ("Sony WH-CH520 Wireless Bluetooth Headphones (50hr Battery)", "Electronics", 4990.0, 3100.0, 3990.0),
        ("Apple iPhone 15 (128 GB, Black)", "Electronics", 79900.0, 62000.0, 69999.0),
        ("Xiaomi Smart Band 8 with AMOLED Display", "Electronics", 3999.0, 1800.0, 2499.0),
        ("TP-Link Archer C6 AC1200 Dual Band Gigabit Wi-Fi Router", "Electronics", 3499.0, 1600.0, 2199.0),

        # Fashion & Apparel
        ("Levi's Men Slim Fit Washed Denim Jeans", "Fashion & Apparel", 3499.0, 1400.0, 2199.0),
        ("BIBA Women Printed A-Line Cotton Kurti", "Fashion & Apparel", 2499.0, 750.0, 1299.0),
        ("Puma Men Smashic Casual White Sneakers", "Fashion & Apparel", 4499.0, 1600.0, 2249.0),
        ("FabIndia Men Handloom Cotton Kurta", "Fashion & Apparel", 2199.0, 800.0, 1499.0),
        ("Roadster Men Graphic Printed Pure Cotton T-Shirt", "Fashion & Apparel", 999.0, 280.0, 499.0),
        ("Allen Solly Men Regular Fit Formal Cotton Shirt", "Fashion & Apparel", 2199.0, 850.0, 1399.0),
        ("W for Woman Solid Rayon Straight Palazzos", "Fashion & Apparel", 1699.0, 500.0, 899.0),
        ("Fastrack Casual Daypack Backpack (28 Litres)", "Fashion & Apparel", 1995.0, 650.0, 999.0),
        ("Aurelia Women Embroidered Chanderi Silk Dupatta", "Fashion & Apparel", 1499.0, 420.0, 749.0),
        ("Red Tape Men Memory Foam Running Shoes", "Fashion & Apparel", 5499.0, 1200.0, 1649.0),
        ("Janasya Women Poly Silk Kurta with Pant Set", "Fashion & Apparel", 3199.0, 900.0, 1399.0),
        ("Peter England Men Classic Fit Chinos Trousers", "Fashion & Apparel", 1999.0, 750.0, 1199.0),
        ("Manyavar Men Jacquard Silk Festive Kurta Pajama Set", "Fashion & Apparel", 4999.0, 1900.0, 3499.0),

        # Home & Kitchen
        ("Prestige Iris 750W Mixer Grinder (3 Stainless Steel Jars)", "Home & Kitchen", 4495.0, 2100.0, 2899.0),
        ("Milton Thermosteel Duo 1000ml Insulated Water Bottle", "Home & Kitchen", 1195.0, 550.0, 849.0),
        ("Pigeon Non-Stick 3-Piece Kitchen Cookware Set", "Home & Kitchen", 2395.0, 850.0, 1199.0),
        ("Kent Grand RO+UV Water Purifier with Mineral ROTM (8L)", "Home & Kitchen", 19500.0, 11500.0, 14499.0),
        ("Solimo Queen Size 100% Cotton Floral Bedsheet with 2 Pillows", "Home & Kitchen", 1800.0, 600.0, 899.0),
        ("Philips Daily Collection 1.5L Electric Kettle (HD9306)", "Home & Kitchen", 2695.0, 1100.0, 1699.0),
        ("Bajaj New Shakti 15L Storage Water Heater (Geyser)", "Home & Kitchen", 9950.0, 4800.0, 5999.0),
        ("Hawkins Contura 3L Hard Anodised Pressure Cooker", "Home & Kitchen", 2150.0, 1250.0, 1749.0),
        ("Cello Opalware Dazzle Tropical Lagoon Dinner Set (18 Pcs)", "Home & Kitchen", 2495.0, 950.0, 1399.0),
        ("Story@Home Blackout 7ft Eyelet Door Curtains (Set of 2)", "Home & Kitchen", 1999.0, 600.0, 899.0),

        # Books & Study Material
        ("Indian Polity by M. Laxmikanth (7th Edition)", "Books & Media", 995.0, 450.0, 649.0),
        ("Atomic Habits by James Clear (Paperback)", "Books & Media", 799.0, 280.0, 449.0),
        ("UPSC General Studies Paper 1 Manual by McGraw Hill", "Books & Media", 1450.0, 650.0, 999.0),
        ("Rich Dad Poor Dad (English / Hindi Edition)", "Books & Media", 499.0, 180.0, 299.0),
        ("NCERT Complete Class 10 & 12 Science/Maths Set", "Books & Media", 1850.0, 800.0, 1299.0),
        ("Word Power Made Easy by Norman Lewis", "Books & Media", 299.0, 90.0, 169.0),
        ("Ikigai: The Japanese Secret to a Long and Happy Life", "Books & Media", 550.0, 190.0, 320.0),
        ("Quantitative Aptitude for Competitive Exams by R.S. Aggarwal", "Books & Media", 875.0, 390.0, 580.0),
        ("The Psychology of Money by Morgan Housel", "Books & Media", 499.0, 180.0, 289.0),

        # Health & Beauty
        ("Mamaearth Vitamin C Face Wash with Turmeric (150ml)", "Health & Beauty", 399.0, 140.0, 279.0),
        ("Himalaya Purifying Neem Face Wash (400ml)", "Health & Beauty", 425.0, 180.0, 299.0),
        ("Biotique Bio Kelp Protein Anti-Hair Fall Shampoo (650ml)", "Health & Beauty", 590.0, 210.0, 369.0),
        ("The Derma Co 10% Niacinamide Serum with Zinc (30ml)", "Health & Beauty", 599.0, 240.0, 449.0),
        ("Wow Skin Science Red Onion Black Seed Hair Oil (200ml)", "Health & Beauty", 599.0, 190.0, 349.0),
        ("Minimalist 10% Vitamin C Serum for Glowing Skin (30ml)", "Health & Beauty", 699.0, 310.0, 549.0),
        ("Nivea Soft Light Moisturizer Cream (300ml)", "Health & Beauty", 550.0, 230.0, 385.0),
        ("Dettol Original Liquid Handwash Refill Pouch (1500ml)", "Health & Beauty", 349.0, 160.0, 249.0)
    ]

    prod_id_to_base_price = {}
    prod_id_to_current_price = {}

    for i in range(len(df_prod)):
        template = indian_product_catalog[i % len(indian_product_catalog)]
        # Add slight variation to template name if repeating
        suffix = f" (Edition {i // len(indian_product_catalog) + 1})" if i >= len(indian_product_catalog) else ""
        name = template[0] + suffix
        category = template[1]
        
        # Adjust price slightly per instance
        jitter = random.uniform(0.92, 1.08)
        base = round(template[2] * jitter, 2)
        cost = round(template[3] * jitter, 2)
        current = round(template[4] * jitter, 2)
        
        df_prod.at[i, 'name'] = name
        df_prod.at[i, 'category'] = category
        df_prod.at[i, 'base_price'] = base
        df_prod.at[i, 'cost_price'] = cost
        df_prod.at[i, 'current_price'] = current
        
        p_id = df_prod.at[i, 'id']
        prod_id_to_base_price[p_id] = base
        prod_id_to_current_price[p_id] = current

    df_prod.to_csv(prod_path, index=False)
    print(f"✓ Updated {len(df_prod)} products with authentic Indian SKUs and realistic INR pricing.")

    # --- Update competitor_prices.csv ---
    comp_path = os.path.join(raw_dir, 'competitor_prices.csv')
    df_comp = pd.read_csv(comp_path)
    indian_competitors = ["Flipkart", "Amazon India", "Meesho", "Myntra", "Reliance Digital", "Croma", "Tata CLiQ"]

    for i in range(len(df_comp)):
        p_id = df_comp.at[i, 'product_id']
        base = prod_id_to_base_price.get(p_id, 2499.0)
        df_comp.at[i, 'competitor_name'] = random.choice(indian_competitors)
        # Competitor price within 85% to 105% of base price
        df_comp.at[i, 'competitor_price'] = round(base * random.uniform(0.85, 1.02), 2)

    df_comp.to_csv(comp_path, index=False)
    print(f"✓ Updated {len(df_comp)} competitor prices with Indian retailers (Flipkart, Amazon India, Meesho, etc.).")

    # --- Update orders.csv prices to match product prices ---
    orders_path = os.path.join(raw_dir, 'orders.csv')
    df_orders = pd.read_csv(orders_path)

    for i in range(len(df_orders)):
        p_id = df_orders.at[i, 'product_id']
        curr = prod_id_to_current_price.get(p_id, 1499.0)
        qty = df_orders.at[i, 'quantity']
        disc_pct = random.choice([0.0, 0.05, 0.10, 0.15, 0.20]) if df_orders.at[i, 'is_flash_sale'] else 0.0
        raw_total = curr * qty
        disc_amt = round(raw_total * disc_pct, 2)
        paid = round(max(100.0, raw_total - disc_amt), 2)
        
        df_orders.at[i, 'price_paid'] = paid
        df_orders.at[i, 'discount_applied'] = disc_amt

    df_orders.to_csv(orders_path, index=False)
    print(f"✓ Updated {len(df_orders)} historical orders with scaled realistic INR totals.")

if __name__ == '__main__':
    localize_data()
