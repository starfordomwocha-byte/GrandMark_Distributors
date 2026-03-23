from app import app, db, Product, Ledger

# --- THE GRANDMARK GLOBAL MASTER INVENTORY: KENYAN EDITION (115+ ITEMS) ---
master_b2b_inventory = [
    # =========================================================
    # --- CEREALS, FLOURS & DRY GRAINS ---
    # =========================================================
    {"name": "Soko Maize Meal (Bale: 12 x 2kg)", "sku": "DRY-MZ-SK2K12", "category": "Dry Groceries", "buying_price": 1850.00, "unit_cost": 2100.00, "stock_quantity": 850},
    {"name": "Jogoo Maize Meal (Bale: 12 x 2kg)", "sku": "DRY-MZ-JG2K12", "category": "Dry Groceries", "buying_price": 1900.00, "unit_cost": 2200.00, "stock_quantity": 420},
    {"name": "Pembe Maize Meal (Bale: 12 x 2kg)", "sku": "DRY-MZ-PM2K12", "category": "Dry Groceries", "buying_price": 1880.00, "unit_cost": 2150.00, "stock_quantity": 500},
    {"name": "Exe All-Purpose Wheat Flour (Bale: 12 x 2kg)", "sku": "DRY-WH-EX2K12", "category": "Dry Groceries", "buying_price": 2000.00, "unit_cost": 2250.00, "stock_quantity": 620},
    {"name": "Ajab Wheat Flour (Bale: 12 x 2kg)", "sku": "DRY-WH-AJ2K12", "category": "Dry Groceries", "buying_price": 1980.00, "unit_cost": 2230.00, "stock_quantity": 450},
    {"name": "Ndovu Atta Mark 1 Flour (Bale: 12 x 2kg)", "sku": "DRY-WH-ND2K12", "category": "Dry Groceries", "buying_price": 2150.00, "unit_cost": 2350.00, "stock_quantity": 180},
    {"name": "Pearl Mwea Pishori Rice (Sack: 25kg)", "sku": "DRY-RC-PL25K", "category": "Dry Groceries", "buying_price": 4200.00, "unit_cost": 4800.00, "stock_quantity": 340},
    {"name": "Daawat Long Grain Basmati (Sack: 25kg)", "sku": "DRY-RC-DW25K", "category": "Dry Groceries", "buying_price": 3800.00, "unit_cost": 4500.00, "stock_quantity": 210},
    {"name": "Ranee Everyday Rice (Sack: 25kg)", "sku": "DRY-RC-RN25K", "category": "Dry Groceries", "buying_price": 2900.00, "unit_cost": 3400.00, "stock_quantity": 500},
    {"name": "Kabras Premium White Sugar (Bale: 20 x 1kg)", "sku": "DRY-SG-KB1K20", "category": "Dry Groceries", "buying_price": 2500.00, "unit_cost": 2900.00, "stock_quantity": 1200},
    {"name": "Nutrameal Brown Sugar (Bale: 20 x 1kg)", "sku": "DRY-SG-NT1K20", "category": "Dry Groceries", "buying_price": 2700.00, "unit_cost": 3100.00, "stock_quantity": 850},
    {"name": "Santa Lucia Spaghetti (Carton: 40 x 400g)", "sku": "DRY-PS-SL400", "category": "Dry Groceries", "buying_price": 2800.00, "unit_cost": 3200.00, "stock_quantity": 410},
    {"name": "Kensalt Iodized Table Salt (Bale: 40 x 500g)", "sku": "DRY-SL-KS500", "category": "Dry Groceries", "buying_price": 1200.00, "unit_cost": 1500.00, "stock_quantity": 950},
    {"name": "Nyahururu Green Grams / Ndengu (Sack: 50kg)", "sku": "DRY-BN-ND50K", "category": "Dry Groceries", "buying_price": 6500.00, "unit_cost": 8200.00, "stock_quantity": 60},
    {"name": "Wairimu Red Beans (Sack: 90kg)", "sku": "DRY-BN-WR90K", "category": "Dry Groceries", "buying_price": 9800.00, "unit_cost": 11800.00, "stock_quantity": 45},

    # =========================================================
    # --- SPICES, SAUCES & CONDIMENTS ---
    # =========================================================
    {"name": "Peptang Tomato Sauce (Carton: 12 x 500g)", "sku": "CND-TM-PT500", "category": "Spices & Condiments", "buying_price": 1750.00, "unit_cost": 2100.00, "stock_quantity": 450},
    {"name": "Peptang Chilli Sauce (Carton: 12 x 250g)", "sku": "CND-CH-PT250", "category": "Spices & Condiments", "buying_price": 1400.00, "unit_cost": 1650.00, "stock_quantity": 320},
    {"name": "Heinz Tomato Ketchup (Carton: 12 x 400g)", "sku": "CND-TM-HZ400", "category": "Spices & Condiments", "buying_price": 3100.00, "unit_cost": 3800.00, "stock_quantity": 150},
    {"name": "Royco Mchuzi Mix - Beef (Carton: 24 x 200g)", "sku": "CND-SP-RYB200", "category": "Spices & Condiments", "buying_price": 3800.00, "unit_cost": 4400.00, "stock_quantity": 1200},
    {"name": "Royco Mchuzi Mix - Chicken (Carton: 24 x 200g)", "sku": "CND-SP-RYC200", "category": "Spices & Condiments", "buying_price": 3800.00, "unit_cost": 4400.00, "stock_quantity": 900},
    {"name": "Knorr Beef Cubes (Box: 100 pcs)", "sku": "CND-SP-KNB100", "category": "Spices & Condiments", "buying_price": 350.00, "unit_cost": 450.00, "stock_quantity": 1100},
    {"name": "Tropical Heat Pilau Masala (Carton: 24 x 100g)", "sku": "CND-SP-THP100", "category": "Spices & Condiments", "buying_price": 2000.00, "unit_cost": 2400.00, "stock_quantity": 290},
    {"name": "Tropical Heat Curry Powder (Carton: 24 x 100g)", "sku": "CND-SP-THC100", "category": "Spices & Condiments", "buying_price": 1800.00, "unit_cost": 2200.00, "stock_quantity": 310},
    {"name": "Tropical Heat Tea Masala (Carton: 24 x 100g)", "sku": "CND-SP-THT100", "category": "Spices & Condiments", "buying_price": 2100.00, "unit_cost": 2500.00, "stock_quantity": 180},

    # =========================================================
    # --- COOKING OILS & FATS ---
    # =========================================================
    {"name": "Fresh Fri Vegetable Oil (20L Jerrican)", "sku": "OIL-VG-FF20L", "category": "Oils & Fats", "buying_price": 4100.00, "unit_cost": 4600.00, "stock_quantity": 320},
    {"name": "Fresh Fri Vegetable Oil (Carton: 6 x 3L)", "sku": "OIL-VG-FF3L6", "category": "Oils & Fats", "buying_price": 3900.00, "unit_cost": 4400.00, "stock_quantity": 410},
    {"name": "Golden Fry Cooking Oil (Carton: 12 x 1L)", "sku": "OIL-VG-GF1L12", "category": "Oils & Fats", "buying_price": 2900.00, "unit_cost": 3400.00, "stock_quantity": 580},
    {"name": "Salit Vegetable Oil (Carton: 12 x 1L)", "sku": "OIL-VG-SL1L12", "category": "Oils & Fats", "buying_price": 2850.00, "unit_cost": 3300.00, "stock_quantity": 400},
    {"name": "Elianto Pure Corn Oil (Carton: 6 x 3L)", "sku": "OIL-CR-EL3L6", "category": "Oils & Fats", "buying_price": 4800.00, "unit_cost": 5400.00, "stock_quantity": 140},
    {"name": "Kimbo Solid Cooking Fat (Carton: 12 x 1kg)", "sku": "FAT-SL-KB1K", "category": "Oils & Fats", "buying_price": 2800.00, "unit_cost": 3200.00, "stock_quantity": 560},
    {"name": "Kimbo Solid Cooking Fat (Carton: 24 x 500g)", "sku": "FAT-SL-KB500", "category": "Oils & Fats", "buying_price": 2950.00, "unit_cost": 3400.00, "stock_quantity": 300},
    {"name": "Cowboy Cooking Fat (Carton: 12 x 1kg)", "sku": "FAT-SL-CB1K", "category": "Oils & Fats", "buying_price": 2800.00, "unit_cost": 3200.00, "stock_quantity": 250},
    {"name": "Blue Band Margarine Spread (Carton: 24 x 500g)", "sku": "FAT-MG-BB500", "category": "Oils & Fats", "buying_price": 4200.00, "unit_cost": 4800.00, "stock_quantity": 420}, 
    {"name": "Blue Band Margarine Spread (Carton: 48 x 250g)", "sku": "FAT-MG-BB250", "category": "Oils & Fats", "buying_price": 4500.00, "unit_cost": 5100.00, "stock_quantity": 380}, 
    {"name": "Prestige Margarine (Carton: 24 x 500g)", "sku": "FAT-MG-PR500", "category": "Oils & Fats", "buying_price": 3800.00, "unit_cost": 4300.00, "stock_quantity": 150},

    # =========================================================
    # --- DAIRY & BREAKFAST ---
    # =========================================================
    {"name": "Brookside Whole UHT Milk (Carton: 12 x 500ml)", "sku": "DRY-ML-BR500", "category": "Dairy & Breakfast", "buying_price": 550.00, "unit_cost": 650.00, "stock_quantity": 2500},
    {"name": "Brookside Low Fat UHT Milk (Carton: 12 x 500ml)", "sku": "DRY-ML-BRL500", "category": "Dairy & Breakfast", "buying_price": 580.00, "unit_cost": 680.00, "stock_quantity": 800},
    {"name": "Tuzo Long Life Milk (Carton: 12 x 500ml)", "sku": "DRY-ML-TZ500", "category": "Dairy & Breakfast", "buying_price": 530.00, "unit_cost": 630.00, "stock_quantity": 1100},
    {"name": "KCC Gold Crown UHT Milk (Carton: 12 x 500ml)", "sku": "DRY-ML-KCC500", "category": "Dairy & Breakfast", "buying_price": 540.00, "unit_cost": 640.00, "stock_quantity": 1500},
    {"name": "Delamere Vanilla Yoghurt (Carton: 24 x 250ml)", "sku": "DRY-YG-DL250", "category": "Dairy & Breakfast", "buying_price": 1350.00, "unit_cost": 1600.00, "stock_quantity": 380},
    {"name": "Bio Strawberry Yoghurt (Carton: 12 x 450ml)", "sku": "DRY-YG-BIO450", "category": "Dairy & Breakfast", "buying_price": 1800.00, "unit_cost": 2100.00, "stock_quantity": 250},
    {"name": "Proctor & Allan Oats (Carton: 12 x 500g)", "sku": "BRK-OT-PA500", "category": "Dairy & Breakfast", "buying_price": 3100.00, "unit_cost": 3600.00, "stock_quantity": 180},
    {"name": "Weetabix Original Cereal (Carton: 12 x 400g)", "sku": "BRK-CR-WT400", "category": "Dairy & Breakfast", "buying_price": 4800.00, "unit_cost": 5500.00, "stock_quantity": 420},
    {"name": "Zesta Strawberry Jam (Carton: 12 x 500g)", "sku": "BRK-SP-ZS500", "category": "Dairy & Breakfast", "buying_price": 2900.00, "unit_cost": 3400.00, "stock_quantity": 290},
    {"name": "Zesta Plum Jam (Carton: 12 x 500g)", "sku": "BRK-SP-ZP500", "category": "Dairy & Breakfast", "buying_price": 2900.00, "unit_cost": 3400.00, "stock_quantity": 210},
    {"name": "Zesta Peanut Butter (Carton: 12 x 400g)", "sku": "BRK-SP-ZPB400", "category": "Dairy & Breakfast", "buying_price": 3400.00, "unit_cost": 3900.00, "stock_quantity": 320},

    # =========================================================
    # --- BEVERAGES (HOT & COLD) ---
    # =========================================================
    {"name": "Ketepa Pride Tea Bags (Carton: 24 x 100s)", "sku": "BEV-HT-KT100", "category": "Beverages", "buying_price": 4800.00, "unit_cost": 5500.00, "stock_quantity": 450},
    {"name": "Kericho Gold Loose Leaf (Bale: 20 x 500g)", "sku": "BEV-HT-KG500", "category": "Beverages", "buying_price": 5400.00, "unit_cost": 6200.00, "stock_quantity": 380},
    {"name": "Nescafe Classic Coffee (Carton: 12 x 250g)", "sku": "BEV-HT-NS250", "category": "Beverages", "buying_price": 7200.00, "unit_cost": 8400.00, "stock_quantity": 120},
    {"name": "Milo Energy Drink Powder (Carton: 12 x 400g)", "sku": "BEV-HT-ML400", "category": "Beverages", "buying_price": 5500.00, "unit_cost": 6200.00, "stock_quantity": 250},
    {"name": "Cadbury Drinking Chocolate (Carton: 12 x 400g)", "sku": "BEV-HT-CD400", "category": "Beverages", "buying_price": 4100.00, "unit_cost": 4800.00, "stock_quantity": 210},
    {"name": "Coca-Cola Soda (Pallet: 50 Crates x 300ml)", "sku": "BEV-CL-CC50", "category": "Beverages", "buying_price": 38000.00, "unit_cost": 45000.00, "stock_quantity": 35},
    {"name": "Sprite Soda (Pallet: 50 Crates x 300ml)", "sku": "BEV-CL-SP50", "category": "Beverages", "buying_price": 38000.00, "unit_cost": 45000.00, "stock_quantity": 28},
    {"name": "Fanta Orange Soda (Pallet: 50 Crates x 300ml)", "sku": "BEV-CL-FO50", "category": "Beverages", "buying_price": 38000.00, "unit_cost": 45000.00, "stock_quantity": 30},
    {"name": "Afia Tropical Juice (Carton: 12 x 500ml)", "sku": "BEV-CL-AF500", "category": "Beverages", "buying_price": 750.00, "unit_cost": 900.00, "stock_quantity": 650},
    {"name": "Afia Mango Juice (Carton: 12 x 500ml)", "sku": "BEV-CL-AFM500", "category": "Beverages", "buying_price": 750.00, "unit_cost": 900.00, "stock_quantity": 520},
    {"name": "Quencher Life Mango (Carton: 12 x 1L)", "sku": "BEV-CL-QM1L", "category": "Beverages", "buying_price": 1400.00, "unit_cost": 1700.00, "stock_quantity": 210},
    {"name": "Aquamist Mineral Water (Carton: 24 x 500ml)", "sku": "BEV-CL-AQ500", "category": "Beverages", "buying_price": 480.00, "unit_cost": 600.00, "stock_quantity": 3200},
    {"name": "Dasani Purified Water (Carton: 24 x 500ml)", "sku": "BEV-CL-DS500", "category": "Beverages", "buying_price": 550.00, "unit_cost": 700.00, "stock_quantity": 2100},
    {"name": "Monster Energy Drink (Carton: 24 x 500ml)", "sku": "BEV-CL-MN500", "category": "Beverages", "buying_price": 3800.00, "unit_cost": 4500.00, "stock_quantity": 140}, 
    {"name": "Red Bull Energy Drink (Carton: 24 x 250ml)", "sku": "BEV-CL-RB250", "category": "Beverages", "buying_price": 4200.00, "unit_cost": 4800.00, "stock_quantity": 110}, 

    # =========================================================
    # --- FROZEN FOODS & BULK MEAT ---
    # =========================================================
    {"name": "Farmer's Choice Beef Sausages (Carton: 20 x 400g)", "sku": "FRZ-MT-FCB400", "category": "Frozen Foods", "buying_price": 5400.00, "unit_cost": 6200.00, "stock_quantity": 110},
    {"name": "Farmer's Choice Pork Sausages (Carton: 20 x 400g)", "sku": "FRZ-MT-FCP400", "category": "Frozen Foods", "buying_price": 5600.00, "unit_cost": 6400.00, "stock_quantity": 90},
    {"name": "Farmer's Choice Smokies (Carton: 20 x 500g)", "sku": "FRZ-MT-FCS500", "category": "Frozen Foods", "buying_price": 6000.00, "unit_cost": 6800.00, "stock_quantity": 150},
    {"name": "Kenchic Frozen Whole Chicken (Carton: 10 x 1.2kg)", "sku": "FRZ-MT-KCWC12", "category": "Frozen Foods", "buying_price": 4600.00, "unit_cost": 5500.00, "stock_quantity": 85},
    {"name": "Kenchic Chicken Drumsticks (Carton: 10 x 1kg)", "sku": "FRZ-MT-KCD10", "category": "Frozen Foods", "buying_price": 5200.00, "unit_cost": 6000.00, "stock_quantity": 40},

    # =========================================================
    # --- SNACKS & CONFECTIONERY ---
    # =========================================================
    {"name": "Krackles Potato Crisps - Salted (Carton: 48 x 50g)", "sku": "SNK-CR-KRS50", "category": "Snacks & Sweets", "buying_price": 1900.00, "unit_cost": 2400.00, "stock_quantity": 420},
    {"name": "Krackles Potato Crisps - Onion (Carton: 48 x 50g)", "sku": "SNK-CR-KRO50", "category": "Snacks & Sweets", "buying_price": 1900.00, "unit_cost": 2400.00, "stock_quantity": 380},
    {"name": "Tropical Heat Chevda - Mild (Carton: 24 x 200g)", "sku": "SNK-CR-THC200", "category": "Snacks & Sweets", "buying_price": 3200.00, "unit_cost": 3800.00, "stock_quantity": 150},
    {"name": "NuVita Digestive Biscuits (Carton: 24 x 400g)", "sku": "SNK-BS-NV400", "category": "Snacks & Sweets", "buying_price": 3100.00, "unit_cost": 3600.00, "stock_quantity": 310},
    {"name": "NuVita Ginger Snaps (Carton: 24 x 200g)", "sku": "SNK-BS-NVG200", "category": "Snacks & Sweets", "buying_price": 2400.00, "unit_cost": 2800.00, "stock_quantity": 280},
    {"name": "Manji Marie Biscuits (Carton: 48 x 150g)", "sku": "SNK-BS-MJ150", "category": "Snacks & Sweets", "buying_price": 2400.00, "unit_cost": 2800.00, "stock_quantity": 550},
    {"name": "Cadbury Dairy Milk Chocolate (Display Box: 24 x 50g)", "sku": "SNK-CH-CDM50", "category": "Snacks & Sweets", "buying_price": 1400.00, "unit_cost": 1800.00, "stock_quantity": 95},
    {"name": "Wrigley's PK Chewing Gum (Display Box: 30 pks)", "sku": "SNK-GM-PK30", "category": "Snacks & Sweets", "buying_price": 950.00, "unit_cost": 1200.00, "stock_quantity": 800},
    {"name": "Wrigley's Doublemint Gum (Display Box: 30 pks)", "sku": "SNK-GM-DM30", "category": "Snacks & Sweets", "buying_price": 950.00, "unit_cost": 1200.00, "stock_quantity": 750},

    # =========================================================
    # --- HOME CARE & CLEANING ---
    # =========================================================
    {"name": "Omo Washing Powder (Sack: 10kg)", "sku": "CLN-PW-OM10K", "category": "Home Cleaning", "buying_price": 2100.00, "unit_cost": 2500.00, "stock_quantity": 450},
    {"name": "Omo Hand Wash Powder (Carton: 24 x 500g)", "sku": "CLN-PW-OM500", "category": "Home Cleaning", "buying_price": 3400.00, "unit_cost": 3900.00, "stock_quantity": 320},
    {"name": "Ariel Machine Detergent (Carton: 6 x 2kg)", "sku": "CLN-PW-AR2K", "category": "Home Cleaning", "buying_price": 3200.00, "unit_cost": 3800.00, "stock_quantity": 180},
    {"name": "Sunlight Liquid Dishwash (Carton: 12 x 1L)", "sku": "CLN-LQ-SL1L", "category": "Home Cleaning", "buying_price": 1750.00, "unit_cost": 2100.00, "stock_quantity": 320},
    {"name": "Sunlight Liquid Dishwash (Carton: 24 x 500ml)", "sku": "CLN-LQ-SL500", "category": "Home Cleaning", "buying_price": 2100.00, "unit_cost": 2500.00, "stock_quantity": 400},
    {"name": "Ushindi Bar Soap (Carton: 25 x 800g)", "sku": "CLN-BR-US800", "category": "Home Cleaning", "buying_price": 2800.00, "unit_cost": 3300.00, "stock_quantity": 550},
    {"name": "Menengai Bar Soap (Carton: 25 x 800g)", "sku": "CLN-BR-MG800", "category": "Home Cleaning", "buying_price": 2900.00, "unit_cost": 3500.00, "stock_quantity": 600},
    {"name": "Jamaa Cream Bar Soap (Carton: 25 x 800g)", "sku": "CLN-BR-JM800", "category": "Home Cleaning", "buying_price": 2850.00, "unit_cost": 3400.00, "stock_quantity": 480},
    {"name": "Toilex Tissue Paper (Bale: 40 Rolls)", "sku": "CLN-PP-TL40", "category": "Home Cleaning", "buying_price": 950.00, "unit_cost": 1200.00, "stock_quantity": 1500},
    {"name": "Velvex Premium Tissue (Bale: 40 Rolls)", "sku": "CLN-PP-VX40", "category": "Home Cleaning", "buying_price": 1400.00, "unit_cost": 1800.00, "stock_quantity": 800},
    {"name": "Velvex Kitchen Towels (Bale: 24 Rolls)", "sku": "CLN-PP-VXKT24", "category": "Home Cleaning", "buying_price": 1600.00, "unit_cost": 2000.00, "stock_quantity": 420},
    {"name": "Jik Bleach / Disinfectant (Carton: 12 x 750ml)", "sku": "CLN-LQ-JK750", "category": "Home Cleaning", "buying_price": 1400.00, "unit_cost": 1800.00, "stock_quantity": 280},
    {"name": "Harpic Toilet Bowl Cleaner (Carton: 12 x 500ml)", "sku": "CLN-LQ-HP500", "category": "Home Cleaning", "buying_price": 1700.00, "unit_cost": 2100.00, "stock_quantity": 220},
    {"name": "Doom Insecticide Spray (Carton: 24 x 400ml)", "sku": "CLN-AR-DM400", "category": "Home Cleaning", "buying_price": 5400.00, "unit_cost": 6500.00, "stock_quantity": 150},
    {"name": "Mortein Doom Spray (Carton: 24 x 400ml)", "sku": "CLN-AR-MD400", "category": "Home Cleaning", "buying_price": 5600.00, "unit_cost": 6700.00, "stock_quantity": 120},

    # =========================================================
    # --- PERSONAL CARE & HYGIENE ---
    # =========================================================
    {"name": "Geisha Aloe Vera Soap (Carton: 48 x 175g)", "sku": "BTY-SP-GSA175", "category": "Personal Care", "buying_price": 4100.00, "unit_cost": 4800.00, "stock_quantity": 520},
    {"name": "Geisha Rose Soap (Carton: 48 x 175g)", "sku": "BTY-SP-GSR175", "category": "Personal Care", "buying_price": 4100.00, "unit_cost": 4800.00, "stock_quantity": 480},
    {"name": "Dettol Original Soap (Carton: 48 x 175g)", "sku": "BTY-SP-DT175", "category": "Personal Care", "buying_price": 4500.00, "unit_cost": 5200.00, "stock_quantity": 340},
    {"name": "Imperial Leather Classic (Carton: 48 x 175g)", "sku": "BTY-SP-IL175", "category": "Personal Care", "buying_price": 4300.00, "unit_cost": 5000.00, "stock_quantity": 290},
    {"name": "Colgate Herbal Toothpaste (Carton: 36 x 100g)", "sku": "BTY-OR-CG100", "category": "Personal Care", "buying_price": 2900.00, "unit_cost": 3600.00, "stock_quantity": 610},
    {"name": "Close-Up Red Hot Toothpaste (Carton: 36 x 100g)", "sku": "BTY-OR-CU100", "category": "Personal Care", "buying_price": 2800.00, "unit_cost": 3400.00, "stock_quantity": 420},
    {"name": "Valon Petroleum Jelly (Carton: 24 x 250g)", "sku": "BTY-SK-VL250", "category": "Personal Care", "buying_price": 2200.00, "unit_cost": 2800.00, "stock_quantity": 450},
    {"name": "Arimis Milking Jelly (Carton: 24 x 250g)", "sku": "BTY-SK-AR250", "category": "Personal Care", "buying_price": 1800.00, "unit_cost": 2400.00, "stock_quantity": 1200},
    {"name": "Arimis Milking Jelly (Carton: 48 x 100g)", "sku": "BTY-SK-AR100", "category": "Personal Care", "buying_price": 2100.00, "unit_cost": 2800.00, "stock_quantity": 850},
    {"name": "Always Ultra Sanitary Pads (Carton: 24 packs x 8s)", "sku": "BTY-FH-ALU8", "category": "Personal Care", "buying_price": 1800.00, "unit_cost": 2200.00, "stock_quantity": 580},
    {"name": "Always Maxi Thick Pads (Carton: 24 packs x 8s)", "sku": "BTY-FH-ALM8", "category": "Personal Care", "buying_price": 1600.00, "unit_cost": 2000.00, "stock_quantity": 450},

    # =========================================================
    # --- BABY CARE ---
    # =========================================================
    {"name": "Pampers Baby-Dry Size 3 (Bale: 4 x 40s)", "sku": "BBY-DP-PM3", "category": "Baby Care", "buying_price": 3100.00, "unit_cost": 3800.00, "stock_quantity": 320},
    {"name": "Pampers Baby-Dry Size 4 (Bale: 4 x 36s)", "sku": "BBY-DP-PM4", "category": "Baby Care", "buying_price": 3100.00, "unit_cost": 3800.00, "stock_quantity": 290},
    {"name": "Huggies Gold Size 3 (Bale: 4 x 40s)", "sku": "BBY-DP-HG3", "category": "Baby Care", "buying_price": 3400.00, "unit_cost": 4100.00, "stock_quantity": 210},
    {"name": "Softcare Baby Diapers Size 3 (Bale: 4 x 40s)", "sku": "BBY-DP-SC3", "category": "Baby Care", "buying_price": 2600.00, "unit_cost": 3200.00, "stock_quantity": 500},
    {"name": "Softcare Baby Wipes (Carton: 24 packs x 80s)", "sku": "BBY-WP-SC80", "category": "Baby Care", "buying_price": 3100.00, "unit_cost": 3800.00, "stock_quantity": 410},
    {"name": "Johnson's Baby Powder (Carton: 24 x 200g)", "sku": "BBY-SK-JBP200", "category": "Baby Care", "buying_price": 3400.00, "unit_cost": 4200.00, "stock_quantity": 150},
    {"name": "Johnson's Baby Oil (Carton: 24 x 200ml)", "sku": "BBY-SK-JBO200", "category": "Baby Care", "buying_price": 3800.00, "unit_cost": 4600.00, "stock_quantity": 110},

    # =========================================================
    # --- STATIONERY & BASIC HOME ---
    # =========================================================
    {"name": "Chui Matchboxes (Carton: 10 bundles)", "sku": "HDW-MT-CH100", "category": "Stationery & Home", "buying_price": 350.00, "unit_cost": 450.00, "stock_quantity": 850},
    {"name": "Rhino Matchboxes (Carton: 10 bundles)", "sku": "HDW-MT-RH100", "category": "Stationery & Home", "buying_price": 340.00, "unit_cost": 440.00, "stock_quantity": 600},
    {"name": "Eveready AA Batteries (Display Card: 24 pairs)", "sku": "HDW-BT-EV24", "category": "Stationery & Home", "buying_price": 1900.00, "unit_cost": 2400.00, "stock_quantity": 340},
    {"name": "Energizer AA Batteries (Display Card: 24 pairs)", "sku": "HDW-BT-EN24", "category": "Stationery & Home", "buying_price": 2600.00, "unit_cost": 3200.00, "stock_quantity": 150},
    {"name": "Kasuku A5 Exercise Books (Carton: 120 pcs)", "sku": "STN-BK-KS120", "category": "Stationery & Home", "buying_price": 3800.00, "unit_cost": 4500.00, "stock_quantity": 210},
    {"name": "Kasuku A4 200pg Ruled Books (Carton: 48 pcs)", "sku": "STN-BK-KSA4", "category": "Stationery & Home", "buying_price": 4200.00, "unit_cost": 5000.00, "stock_quantity": 180},
    {"name": "BIC Ballpoint Pens - Blue (Box: 50 pcs)", "sku": "STN-PN-BCB50", "category": "Stationery & Home", "buying_price": 850.00, "unit_cost": 1100.00, "stock_quantity": 300},
    {"name": "BIC Ballpoint Pens - Black (Box: 50 pcs)", "sku": "STN-PN-BCK50", "category": "Stationery & Home", "buying_price": 850.00, "unit_cost": 1100.00, "stock_quantity": 250},

    # =========================================================
    # --- HARDWARE & CONSTRUCTION ---
    # =========================================================
    {"name": "Bamburi Portland Cement 50kg (Pallet: 40 Bags)", "sku": "BLD-CM-BB50", "category": "Building Materials", "buying_price": 29000.00, "unit_cost": 34000.00, "stock_quantity": 150},
    {"name": "Simba Cement 50kg (Pallet: 40 Bags)", "sku": "BLD-CM-SM50", "category": "Building Materials", "buying_price": 28000.00, "unit_cost": 33000.00, "stock_quantity": 80},
    {"name": "Savannah Cement 50kg (Pallet: 40 Bags)", "sku": "BLD-CM-SV50", "category": "Building Materials", "buying_price": 28500.00, "unit_cost": 33500.00, "stock_quantity": 120},
    {"name": "Crown Paints Vinyl Matt (20L Bucket)", "sku": "BLD-PT-CR20", "category": "Building Materials", "buying_price": 5200.00, "unit_cost": 6500.00, "stock_quantity": 240},
    {"name": "Basco Paints Silk Vinyl (20L Bucket)", "sku": "BLD-PT-BS20", "category": "Building Materials", "buying_price": 4800.00, "unit_cost": 6100.00, "stock_quantity": 180},
    {"name": "Mabati Rolling Mills Dumuzi Sheets (Bundle 20)", "sku": "BLD-RF-MR20", "category": "Building Materials", "buying_price": 18000.00, "unit_cost": 22000.00, "stock_quantity": 110},
    {"name": "Devki D12 Ribbed Steel Rebar (Bundle: 50 pcs)", "sku": "BLD-ST-DVK12", "category": "Building Materials", "buying_price": 42000.00, "unit_cost": 48000.00, "stock_quantity": 95},

    # =========================================================
    # --- ELECTRONICS & APPLIANCES ---
    # =========================================================
    {"name": "Ramtons 1.5L Stainless Steel Kettle", "sku": "APP-KT-RM15", "category": "Electronics & TVs", "buying_price": 1600.00, "unit_cost": 2200.00, "stock_quantity": 65},
    {"name": "Ramtons 20L Digital Microwave Oven", "sku": "APP-MW-RM20", "category": "Electronics & TVs", "buying_price": 6800.00, "unit_cost": 8500.00, "stock_quantity": 22}, 
    {"name": "Mika Standing Fan 16-Inch", "sku": "APP-FN-MK16", "category": "Electronics & TVs", "buying_price": 2400.00, "unit_cost": 3200.00, "stock_quantity": 40},
    {"name": "Von Hotpoint Double Door Fridge 400L", "sku": "APP-FR-VH400", "category": "Heavy Appliances", "buying_price": 62000.00, "unit_cost": 75000.00, "stock_quantity": 15},
    {"name": "Samsung 50-Inch 4K UHD Smart TV", "sku": "TV-50-SM4K", "category": "Electronics & TVs", "buying_price": 65000.00, "unit_cost": 82000.00, "stock_quantity": 25},
    {"name": "Hisense 43-Inch Frameless Smart TV", "sku": "TV-43-HS43", "category": "Electronics & TVs", "buying_price": 32000.00, "unit_cost": 41000.00, "stock_quantity": 42},
    {"name": "Tecno Spark 20 Pro (Carton: 10 units)", "sku": "MOB-AD-TC20P", "category": "Smartphones & IT", "buying_price": 185000.00, "unit_cost": 220000.00, "stock_quantity": 12},
    {"name": "Infinix Hot 40 (Carton: 10 units)", "sku": "MOB-AD-IX40", "category": "Smartphones & IT", "buying_price": 155000.00, "unit_cost": 185000.00, "stock_quantity": 18}
]

def seed_database():
    print("\n" + "="*70)
    print("  GRANDMARK ENTERPRISE DATABASE SYNC: GLOBAL B2B MODULE  ")
    print("="*70 + "\n")
    print("[+] Establishing SQLite pipeline connection...\n")
    
    with app.app_context():
        # --- THE EXCLUSION WIPE ---
        try:
            db.session.query(Product).delete()
            # Purge old automated stocking debits so we don't double-charge the ledger!
            db.session.query(Ledger).filter(Ledger.description.like('%Initial Enterprise Warehouse Stocking%')).delete(synchronize_session=False)
            db.session.commit()
            print("[!] Old inventory and automated ledger charges purged successfully.\n")
        except Exception as e:
            print(f"[ERROR] Failed to purge old inventory: {e}")
            db.session.rollback()

        added_count = 0
        total_expense = 0.0
        
        # Inject the massive localized list
        for item in master_b2b_inventory:
            new_product = Product(
                name=item['name'],
                sku=item['sku'],
                category=item['category'],
                buying_price=item['buying_price'],
                unit_cost=item['unit_cost'],
                stock_quantity=item['stock_quantity']
            )
            db.session.add(new_product)
            added_count += 1
            
            # The Ledger must be charged based on the BUYING PRICE, not the Selling Price
            item_expense = item['buying_price'] * item['stock_quantity']
            total_expense += item_expense
            
            # Terminal output logic
            status = "CRITICAL" if item['stock_quantity'] < 25 else "HEALTHY"
            if item['stock_quantity'] == 0: status = "DEPLETED"
            
            print(f"  -> [INJECTED] SKU: {item['sku']:<15} | {item['name'][:35]:<35} | Vol: {item['stock_quantity']:<4} | Status: {status}")
                
        # --- CHARGE THE LEDGER ---
        initial_stock_debit = Ledger(
            transaction_type='Debit',
            amount=total_expense,
            description="Initial Enterprise Warehouse Stocking (Bulk B2B Purchase)"
        )
        db.session.add(initial_stock_debit)
        
        db.session.commit()
        
        print("\n" + "="*70)
        print(f"  SYSTEM OVERVIEW: {added_count} active localized product lines registered.")
        print(f"  CAPITAL DEPLOYED: KES {total_expense:,.2f}")
        print(f"  CASHBOOK UPDATED: Successfully debited KES {total_expense:,.2f} from the master ledger.")
        print("="*70 + "\n")

if __name__ == "__main__":
    seed_database()