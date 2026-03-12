from app import app, db, Product, Ledger

# --- THE GRANDMARK GLOBAL MASTER INVENTORY (160+ ITEMS) ---
master_b2b_inventory = [
    # =========================================================
    # --- ORIGINAL FMCG & GROCERY CATALOG ---
    # =========================================================

    # --- CATEGORY: CEREALS, FLOURS & DRY GRAINS ---
    {"name": "Premium Maize Flour (Bale: 12 x 2kg)", "sku": "DRY-MZ-2K12", "category": "Dry Groceries", "unit_cost": 2100.00, "stock_quantity": 850},
    {"name": "Fortified Maize Meal (Bale: 24 x 1kg)", "sku": "DRY-MZ-1K24", "category": "Dry Groceries", "unit_cost": 2200.00, "stock_quantity": 420},
    {"name": "All-Purpose Wheat Flour (Bale: 12 x 2kg)", "sku": "DRY-WH-2K12", "category": "Dry Groceries", "unit_cost": 2250.00, "stock_quantity": 620},
    {"name": "Atta Mark 1 Wheat Flour (Bale: 12 x 2kg)", "sku": "DRY-WH-AT2K", "category": "Dry Groceries", "unit_cost": 2350.00, "stock_quantity": 180},
    {"name": "Pure Mwea Pishori Rice (Sack: 25kg)", "sku": "DRY-RC-P25K", "category": "Dry Groceries", "unit_cost": 4800.00, "stock_quantity": 340},
    {"name": "Long Grain Basmati Rice (Sack: 50kg)", "sku": "DRY-RC-B50K", "category": "Dry Groceries", "unit_cost": 8500.00, "stock_quantity": 110},
    {"name": "Biryani Blended Rice (Sack: 25kg)", "sku": "DRY-RC-BR25", "category": "Dry Groceries", "unit_cost": 4200.00, "stock_quantity": 85},
    {"name": "Refined White Sugar (Bale: 20 x 1kg)", "sku": "DRY-SG-W1K20", "category": "Dry Groceries", "unit_cost": 2900.00, "stock_quantity": 1200},
    {"name": "Brown Cane Sugar (Bale: 20 x 1kg)", "sku": "DRY-SG-B1K20", "category": "Dry Groceries", "unit_cost": 3100.00, "stock_quantity": 850},
    {"name": "Dried Rosecoco Beans (Sack: 90kg)", "sku": "DRY-BN-R90K", "category": "Dry Groceries", "unit_cost": 12500.00, "stock_quantity": 45},
    {"name": "Wairimu Red Beans (Sack: 90kg)", "sku": "DRY-BN-W90K", "category": "Dry Groceries", "unit_cost": 11800.00, "stock_quantity": 30},
    {"name": "Dried Green Grams / Ndengu (Sack: 50kg)", "sku": "DRY-GR-G50K", "category": "Dry Groceries", "unit_cost": 8200.00, "stock_quantity": 60},
    {"name": "Black Beans / Njahi (Sack: 50kg)", "sku": "DRY-BN-NJ50", "category": "Dry Groceries", "unit_cost": 9500.00, "stock_quantity": 25},
    {"name": "Spaghetti Pasta (Carton: 40 x 400g)", "sku": "DRY-PS-S400", "category": "Dry Groceries", "unit_cost": 3200.00, "stock_quantity": 410},
    {"name": "Macaroni Pasta (Carton: 40 x 400g)", "sku": "DRY-PS-M400", "category": "Dry Groceries", "unit_cost": 3200.00, "stock_quantity": 280},
    {"name": "Iodized Table Salt (Bale: 40 x 500g)", "sku": "DRY-SL-T500", "category": "Dry Groceries", "unit_cost": 1500.00, "stock_quantity": 950},

    # --- CATEGORY: SPICES, SAUCES & CONDIMENTS ---
    {"name": "Tomato Paste (Carton: 50 x 70g tins)", "sku": "CND-TM-P70G", "category": "Spices & Condiments", "unit_cost": 1800.00, "stock_quantity": 310},
    {"name": "Tomato Sauce / Ketchup (Carton: 12 x 500g)", "sku": "CND-TM-S500", "category": "Spices & Condiments", "unit_cost": 2100.00, "stock_quantity": 450},
    {"name": "Chilli Sauce (Carton: 12 x 250ml)", "sku": "CND-CH-S250", "category": "Spices & Condiments", "unit_cost": 1600.00, "stock_quantity": 280},
    {"name": "Beef Flavor Seasoning Cubes (Box: 100 pcs)", "sku": "CND-SP-BF100", "category": "Spices & Condiments", "unit_cost": 450.00, "stock_quantity": 1200},
    {"name": "Chicken Flavor Seasoning Cubes (Box: 100 pcs)", "sku": "CND-SP-CH100", "category": "Spices & Condiments", "unit_cost": 450.00, "stock_quantity": 1100},
    {"name": "Dark Soy Sauce (Carton: 12 x 700ml)", "sku": "CND-SY-D700", "category": "Spices & Condiments", "unit_cost": 3400.00, "stock_quantity": 150},
    {"name": "White Vinegar (Carton: 12 x 700ml)", "sku": "CND-VN-W700", "category": "Spices & Condiments", "unit_cost": 1900.00, "stock_quantity": 180},
    {"name": "Curry Powder (Carton: 24 x 100g)", "sku": "CND-SP-CR100", "category": "Spices & Condiments", "unit_cost": 2200.00, "stock_quantity": 340},
    {"name": "Pilau Masala (Carton: 24 x 100g)", "sku": "CND-SP-PM100", "category": "Spices & Condiments", "unit_cost": 2400.00, "stock_quantity": 290},

    # --- CATEGORY: COOKING OILS & FATS ---
    {"name": "Pure Vegetable Cooking Oil (20L Jerrican)", "sku": "OIL-VG-20L", "category": "Oils & Fats", "unit_cost": 4600.00, "stock_quantity": 320},
    {"name": "Pure Vegetable Cooking Oil (Carton: 12 x 1L)", "sku": "OIL-VG-1L12", "category": "Oils & Fats", "unit_cost": 3400.00, "stock_quantity": 580},
    {"name": "Triple Refined Sunflower Oil (Carton: 12 x 1L)", "sku": "OIL-SF-1L12", "category": "Oils & Fats", "unit_cost": 3800.00, "stock_quantity": 18},
    {"name": "Corn Oil (Carton: 6 x 3L)", "sku": "OIL-CR-3L6", "category": "Oils & Fats", "unit_cost": 5400.00, "stock_quantity": 140},
    {"name": "Solid Cooking Fat (Carton: 12 x 1kg)", "sku": "FAT-SL-1K12", "category": "Oils & Fats", "unit_cost": 3200.00, "stock_quantity": 560},
    {"name": "Solid Cooking Fat (Carton: 24 x 500g)", "sku": "FAT-SL-500G24", "category": "Oils & Fats", "unit_cost": 3400.00, "stock_quantity": 410},
    {"name": "Premium Margarine Spread (Carton: 24 x 500g)", "sku": "FAT-MG-500G24", "category": "Oils & Fats", "unit_cost": 4800.00, "stock_quantity": 0}, 
    {"name": "Baking Margarine (Carton: 12 x 1kg)", "sku": "FAT-MG-BK1K", "category": "Oils & Fats", "unit_cost": 4500.00, "stock_quantity": 80},

    # --- CATEGORY: DAIRY & BREAKFAST ---
    {"name": "Whole UHT Long Life Milk (Carton: 12 x 500ml)", "sku": "DRY-ML-W500", "category": "Dairy & Breakfast", "unit_cost": 650.00, "stock_quantity": 2500},
    {"name": "Semi-Skimmed UHT Milk (Carton: 12 x 500ml)", "sku": "DRY-ML-S500", "category": "Dairy & Breakfast", "unit_cost": 650.00, "stock_quantity": 1100},
    {"name": "Evaporated Milk Tins (Carton: 48 x 170g)", "sku": "DRY-ML-E170", "category": "Dairy & Breakfast", "unit_cost": 5200.00, "stock_quantity": 210},
    {"name": "Sweetened Condensed Milk (Carton: 24 x 395g)", "sku": "DRY-ML-C395", "category": "Dairy & Breakfast", "unit_cost": 4800.00, "stock_quantity": 140},
    {"name": "Vanilla Yoghurt Cups (Carton: 24 x 250ml)", "sku": "DRY-YG-VN250", "category": "Dairy & Breakfast", "unit_cost": 1600.00, "stock_quantity": 380},
    {"name": "Oatmeal Porridge Oats (Carton: 12 x 500g)", "sku": "BRK-OT-500G", "category": "Dairy & Breakfast", "unit_cost": 3600.00, "stock_quantity": 180},
    {"name": "Corn Flakes Cereal (Carton: 12 x 500g)", "sku": "BRK-CR-CF500", "category": "Dairy & Breakfast", "unit_cost": 4200.00, "stock_quantity": 320},
    {"name": "Peanut Butter (Carton: 12 x 400g)", "sku": "BRK-SP-PB400", "category": "Dairy & Breakfast", "unit_cost": 3800.00, "stock_quantity": 14}, 
    {"name": "Fruit Jam - Mixed Berry (Carton: 12 x 500g)", "sku": "BRK-SP-JM500", "category": "Dairy & Breakfast", "unit_cost": 3400.00, "stock_quantity": 290},
    {"name": "Natural Pure Honey (Carton: 12 x 500g)", "sku": "BRK-SP-HN500", "category": "Dairy & Breakfast", "unit_cost": 7200.00, "stock_quantity": 95},

    # --- CATEGORY: BEVERAGES (HOT & COLD) ---
    {"name": "Premium Black Tea Bags (Carton: 24 x 100s)", "sku": "BEV-HT-TB100", "category": "Beverages", "unit_cost": 5500.00, "stock_quantity": 450},
    {"name": "Loose Leaf Tea PF1 (Bale: 20 x 500g)", "sku": "BEV-HT-LL500", "category": "Beverages", "unit_cost": 6200.00, "stock_quantity": 380},
    {"name": "Instant Coffee Powder (Carton: 12 x 250g)", "sku": "BEV-HT-CF250", "category": "Beverages", "unit_cost": 8400.00, "stock_quantity": 120},
    {"name": "Drinking Chocolate Powder (Carton: 12 x 400g)", "sku": "BEV-HT-DC400", "category": "Beverages", "unit_cost": 4800.00, "stock_quantity": 210},
    {"name": "Carbonated Cola Sodas (Pallet: 50 Crates x 300ml)", "sku": "BEV-CL-SDA50", "category": "Beverages", "unit_cost": 45000.00, "stock_quantity": 35},
    {"name": "Carbonated Lemon Soda (Pallet: 50 Crates x 300ml)", "sku": "BEV-CL-SDL50", "category": "Beverages", "unit_cost": 45000.00, "stock_quantity": 28},
    {"name": "Orange Fruit Juice (Carton: 12 x 1L)", "sku": "BEV-CL-OJ1L", "category": "Beverages", "unit_cost": 1800.00, "stock_quantity": 650},
    {"name": "Tropical Blend Juice (Carton: 12 x 1L)", "sku": "BEV-CL-TJ1L", "category": "Beverages", "unit_cost": 1800.00, "stock_quantity": 540},
    {"name": "Purified Mineral Water (Carton: 24 x 500ml)", "sku": "BEV-CL-WTR500", "category": "Beverages", "unit_cost": 600.00, "stock_quantity": 3200},
    {"name": "Purified Mineral Water (Carton: 12 x 1.5L)", "sku": "BEV-CL-WTR15", "category": "Beverages", "unit_cost": 750.00, "stock_quantity": 1800},
    {"name": "Energy Drink Cans (Carton: 24 x 250ml)", "sku": "BEV-CL-NRG250", "category": "Beverages", "unit_cost": 3200.00, "stock_quantity": 0}, 
    {"name": "Isotonic Sports Drink (Carton: 12 x 500ml)", "sku": "BEV-CL-SPO500", "category": "Beverages", "unit_cost": 1400.00, "stock_quantity": 310},

    # --- CATEGORY: FROZEN FOODS & BULK MEAT ---
    {"name": "Frozen Whole Chicken (Carton: 10 x 1.2kg)", "sku": "FRZ-MT-CH12", "category": "Frozen Foods", "unit_cost": 5500.00, "stock_quantity": 85},
    {"name": "Premium Beef Sausages (Carton: 20 x 400g)", "sku": "FRZ-MT-BS400", "category": "Frozen Foods", "unit_cost": 6200.00, "stock_quantity": 110},
    {"name": "Frozen French Fries / Chips (Carton: 4 x 2.5kg)", "sku": "FRZ-VG-FF25", "category": "Frozen Foods", "unit_cost": 2800.00, "stock_quantity": 240},
    {"name": "Frozen Mixed Vegetables (Carton: 10 x 1kg)", "sku": "FRZ-VG-MX1K", "category": "Frozen Foods", "unit_cost": 2500.00, "stock_quantity": 160},
    {"name": "Vanilla Ice Cream Tubs (Carton: 6 x 2L)", "sku": "FRZ-DS-IC2L", "category": "Frozen Foods", "unit_cost": 4200.00, "stock_quantity": 75},

    # --- CATEGORY: SNACKS & CONFECTIONERY ---
    {"name": "Potato Crisps - Salted (Carton: 48 x 50g)", "sku": "SNK-CR-SLT50", "category": "Snacks & Sweets", "unit_cost": 2400.00, "stock_quantity": 420},
    {"name": "Potato Crisps - Onion & Cheese (Carton: 48 x 50g)", "sku": "SNK-CR-ON50", "category": "Snacks & Sweets", "unit_cost": 2400.00, "stock_quantity": 380},
    {"name": "Digestive Biscuits (Carton: 24 x 400g)", "sku": "SNK-BS-DG400", "category": "Snacks & Sweets", "unit_cost": 3600.00, "stock_quantity": 310},
    {"name": "Cream Sandwich Biscuits (Carton: 48 x 150g)", "sku": "SNK-BS-CR150", "category": "Snacks & Sweets", "unit_cost": 2800.00, "stock_quantity": 550},
    {"name": "Milk Chocolate Bars (Display Box: 24 x 50g)", "sku": "SNK-CH-MLK50", "category": "Snacks & Sweets", "unit_cost": 1800.00, "stock_quantity": 12}, 
    {"name": "Peppermint Chewing Gum (Display Box: 30 pks)", "sku": "SNK-GM-MNT30", "category": "Snacks & Sweets", "unit_cost": 1200.00, "stock_quantity": 800},
    {"name": "Assorted Fruit Lollipops (Display Jar: 100 pcs)", "sku": "SNK-SW-LP100", "category": "Snacks & Sweets", "unit_cost": 500.00, "stock_quantity": 650},
    {"name": "Roasted Peanuts (Carton: 48 x 100g)", "sku": "SNK-NT-RST100", "category": "Snacks & Sweets", "unit_cost": 3200.00, "stock_quantity": 240},
    {"name": "Raw Popcorn Kernels (Sack: 50kg)", "sku": "SNK-PC-RW50K", "category": "Snacks & Sweets", "unit_cost": 6500.00, "stock_quantity": 40},

    # --- CATEGORY: HOME CARE & CLEANING ---
    {"name": "Multi-Purpose Washing Powder (Sack: 10kg)", "sku": "CLN-PW-MP10", "category": "Home Cleaning", "unit_cost": 2500.00, "stock_quantity": 450},
    {"name": "Machine Wash Detergent (Carton: 6 x 2kg)", "sku": "CLN-PW-MW2K", "category": "Home Cleaning", "unit_cost": 3800.00, "stock_quantity": 180},
    {"name": "Liquid Dishwashing Soap (Carton: 12 x 1L)", "sku": "CLN-LQ-DW1L", "category": "Home Cleaning", "unit_cost": 2100.00, "stock_quantity": 320},
    {"name": "All-Purpose Bar Soap (Carton: 25 x 800g)", "sku": "CLN-BR-AP800", "category": "Home Cleaning", "unit_cost": 3500.00, "stock_quantity": 600},
    {"name": "Toilet Tissue Paper (Bale: 40 Rolls, 2-Ply)", "sku": "CLN-PP-TT40", "category": "Home Cleaning", "unit_cost": 1200.00, "stock_quantity": 1500},
    {"name": "Kitchen Paper Towels (Bale: 24 Rolls)", "sku": "CLN-PP-KT24", "category": "Home Cleaning", "unit_cost": 1800.00, "stock_quantity": 420},
    {"name": "Bleach / Disinfectant (Carton: 12 x 750ml)", "sku": "CLN-LQ-BL750", "category": "Home Cleaning", "unit_cost": 1800.00, "stock_quantity": 280},
    {"name": "Pine Floor Cleaner (Carton: 12 x 1L)", "sku": "CLN-LQ-FL1L", "category": "Home Cleaning", "unit_cost": 2400.00, "stock_quantity": 190},
    {"name": "Toilet Bowl Cleaner Liquid (Carton: 12 x 500ml)", "sku": "CLN-LQ-TB500", "category": "Home Cleaning", "unit_cost": 2100.00, "stock_quantity": 220},
    {"name": "Aerosol Air Freshener (Carton: 24 x 300ml)", "sku": "CLN-AR-AF300", "category": "Home Cleaning", "unit_cost": 4200.00, "stock_quantity": 8}, 
    {"name": "Insecticide Spray (Carton: 24 x 400ml)", "sku": "CLN-AR-IN400", "category": "Home Cleaning", "unit_cost": 6500.00, "stock_quantity": 150},
    {"name": "Steel Wool Scouring Pads (Bale: 100 pcs)", "sku": "CLN-HW-SW100", "category": "Home Cleaning", "unit_cost": 1500.00, "stock_quantity": 400},
    {"name": "Sponge Scourers (Carton: 48 pcs)", "sku": "CLN-HW-SP48", "category": "Home Cleaning", "unit_cost": 1200.00, "stock_quantity": 350},

    # --- CATEGORY: PERSONAL CARE & HYGIENE ---
    {"name": "Antibacterial Bath Soap (Carton: 48 x 175g)", "sku": "BTY-SP-AB175", "category": "Personal Care", "unit_cost": 4800.00, "stock_quantity": 520},
    {"name": "Moisturizing Beauty Bar (Carton: 48 x 175g)", "sku": "BTY-SP-MB175", "category": "Personal Care", "unit_cost": 5200.00, "stock_quantity": 340},
    {"name": "Liquid Hand Wash Pump (Carton: 12 x 500ml)", "sku": "BTY-LQ-HW500", "category": "Personal Care", "unit_cost": 3200.00, "stock_quantity": 180},
    {"name": "Fluoride Toothpaste (Carton: 36 x 100g)", "sku": "BTY-OR-TP100", "category": "Personal Care", "unit_cost": 3600.00, "stock_quantity": 610},
    {"name": "Adult Toothbrushes (Display Box: 48 units)", "sku": "BTY-OR-TB48", "category": "Personal Care", "unit_cost": 2400.00, "stock_quantity": 280},
    {"name": "Petroleum Jelly (Carton: 24 x 250g)", "sku": "BTY-SK-PJ250", "category": "Personal Care", "unit_cost": 2800.00, "stock_quantity": 450},
    {"name": "Cocoa Butter Body Lotion (Carton: 12 x 400ml)", "sku": "BTY-SK-CB400", "category": "Personal Care", "unit_cost": 4200.00, "stock_quantity": 210},
    {"name": "Anti-Dandruff Shampoo (Carton: 12 x 400ml)", "sku": "BTY-HR-SH400", "category": "Personal Care", "unit_cost": 4800.00, "stock_quantity": 180},
    {"name": "Men's Roll-On Deodorant (Carton: 24 x 50ml)", "sku": "BTY-BD-MR50", "category": "Personal Care", "unit_cost": 5400.00, "stock_quantity": 2}, 
    {"name": "Women's Body Spray (Carton: 24 x 150ml)", "sku": "BTY-BD-WS150", "category": "Personal Care", "unit_cost": 6200.00, "stock_quantity": 140},
    {"name": "Sanitary Pads - Normal (Carton: 24 packs x 8s)", "sku": "BTY-FH-SP8", "category": "Personal Care", "unit_cost": 2200.00, "stock_quantity": 580},
    {"name": "Cotton Wool Rolls (Bale: 24 x 100g)", "sku": "BTY-CW-R100", "category": "Personal Care", "unit_cost": 1800.00, "stock_quantity": 310},
    {"name": "Disposable Twin-Blade Razors (Display Card: 24s)", "sku": "BTY-RZ-T24", "category": "Personal Care", "unit_cost": 900.00, "stock_quantity": 850},

    # --- CATEGORY: BABY CARE ---
    {"name": "Disposable Diapers - Size 3 (Bale: 4 x 40s)", "sku": "BBY-DP-SZ3", "category": "Baby Care", "unit_cost": 3800.00, "stock_quantity": 320},
    {"name": "Disposable Diapers - Size 4 (Bale: 4 x 36s)", "sku": "BBY-DP-SZ4", "category": "Baby Care", "unit_cost": 3800.00, "stock_quantity": 290},
    {"name": "Baby Wet Wipes (Carton: 24 packs x 80s)", "sku": "BBY-WP-80S", "category": "Baby Care", "unit_cost": 3800.00, "stock_quantity": 410},
    {"name": "Infant Formula Milk Stage 1 (Carton: 12 x 400g)", "sku": "BBY-FD-FM1", "category": "Baby Care", "unit_cost": 12500.00, "stock_quantity": 85},
    {"name": "Baby Powder (Carton: 24 x 200g)", "sku": "BBY-SK-BP200", "category": "Baby Care", "unit_cost": 4200.00, "stock_quantity": 150},
    {"name": "Baby Jelly / Vaseline (Carton: 24 x 250g)", "sku": "BBY-SK-VJ250", "category": "Baby Care", "unit_cost": 3100.00, "stock_quantity": 190},

    # --- CATEGORY: PET SUPPLIES ---
    {"name": "Adult Dog Food - Beef Flavor (Sack: 10kg)", "sku": "PET-DG-BF10", "category": "Pet Supplies", "unit_cost": 3500.00, "stock_quantity": 120},
    {"name": "Puppy Food - Chicken Flavor (Sack: 5kg)", "sku": "PET-DG-CH5", "category": "Pet Supplies", "unit_cost": 2100.00, "stock_quantity": 90},
    {"name": "Dry Cat Food - Tuna Flavor (Sack: 5kg)", "sku": "PET-CT-TN5", "category": "Pet Supplies", "unit_cost": 2200.00, "stock_quantity": 80},
    {"name": "Tinned Dog Meat (Carton: 24 x 400g)", "sku": "PET-DG-TN400", "category": "Pet Supplies", "unit_cost": 4800.00, "stock_quantity": 0}, 
    {"name": "Clumping Cat Litter (Bag: 5kg)", "sku": "PET-CT-LT5", "category": "Pet Supplies", "unit_cost": 850.00, "stock_quantity": 160},

    # --- CATEGORY: STATIONERY & BASIC HOME ---
    {"name": "A4 Photocopy Paper (Box: 5 Reams)", "sku": "STN-PP-A4R5", "category": "Stationery & Home", "unit_cost": 3200.00, "stock_quantity": 450},
    {"name": "Blue Ballpoint Pens (Box: 50 pcs)", "sku": "STN-PN-BL50", "category": "Stationery & Home", "unit_cost": 800.00, "stock_quantity": 600},
    {"name": "A5 Ruled Exercise Books (Carton: 120 pcs)", "sku": "STN-BK-A5R120", "category": "Stationery & Home", "unit_cost": 4500.00, "stock_quantity": 210},
    {"name": "1.5L Stainless Steel Electric Kettle", "sku": "APP-KT-15LSS", "category": "Stationery & Home", "unit_cost": 1800.00, "stock_quantity": 65},
    {"name": "20L Digital Microwave Oven", "sku": "APP-MW-20LDG", "category": "Stationery & Home", "unit_cost": 7500.00, "stock_quantity": 22}, 
    {"name": "Heavy Duty Dry Iron Box (1000W)", "sku": "APP-IR-1000W", "category": "Stationery & Home", "unit_cost": 1500.00, "stock_quantity": 80},
    {"name": "Blender with Grinder Mill (1.5L)", "sku": "APP-BL-15LGR", "category": "Stationery & Home", "unit_cost": 2800.00, "stock_quantity": 45},
    {"name": "Energy Saving LED Bulbs 9W (Carton: 50 pcs)", "sku": "HDW-LT-LED9", "category": "Stationery & Home", "unit_cost": 7500.00, "stock_quantity": 110},
    {"name": "AA Alkaline Batteries (Display Card: 24 pairs)", "sku": "HDW-BT-AA24", "category": "Stationery & Home", "unit_cost": 2400.00, "stock_quantity": 340},
    {"name": "Matches (Carton: 10 bundles x 10 boxes)", "sku": "HDW-MT-CH100", "category": "Stationery & Home", "unit_cost": 450.00, "stock_quantity": 850},

    # =========================================================
    # --- NEW EXPANSION: ELECTRONICS, AUTOMOTIVE & HARDWARE ---
    # =========================================================

    # --- CATEGORY: MOBILE DEVICES & TABLETS ---
    {"name": "Smartphone Pro Max 256GB (Carton: 10 units)", "sku": "MOB-PM-256G10", "category": "Smartphones & IT", "unit_cost": 1450000.00, "stock_quantity": 12},
    {"name": "Mid-Range Android 128GB (Carton: 20 units)", "sku": "MOB-AD-128G20", "category": "Smartphones & IT", "unit_cost": 480000.00, "stock_quantity": 45},
    {"name": "Budget 4G Feature Phones (Carton: 50 units)", "sku": "MOB-FP-4G50", "category": "Smartphones & IT", "unit_cost": 150000.00, "stock_quantity": 80},
    {"name": "10-Inch Corporate Tablets 64GB (Carton: 10 units)", "sku": "MOB-TB-10IN10", "category": "Smartphones & IT", "unit_cost": 350000.00, "stock_quantity": 30},

    # --- CATEGORY: ENTERPRISE IT & COMPUTING ---
    {"name": "Corporate Core i7 Laptops 16GB RAM (Pallet: 5 units)", "sku": "CMP-LT-I7P5", "category": "Smartphones & IT", "unit_cost": 650000.00, "stock_quantity": 18},
    {"name": "Student Edition Celeron Laptops (Pallet: 10 units)", "sku": "CMP-LT-CEL10", "category": "Smartphones & IT", "unit_cost": 320000.00, "stock_quantity": 40},
    {"name": "Wireless Ergonomic Mouse (Carton: 50 units)", "sku": "CMP-AC-MS50", "category": "Smartphones & IT", "unit_cost": 45000.00, "stock_quantity": 120},
    {"name": "1TB External Hard Drives (Carton: 20 units)", "sku": "CMP-AC-HD1T20", "category": "Smartphones & IT", "unit_cost": 120000.00, "stock_quantity": 65},

    # --- CATEGORY: TELEVISIONS & HOME ENTERTAINMENT ---
    {"name": "65-Inch 4K UHD Smart TV (Single Unit)", "sku": "TV-65-4KSMT", "category": "Electronics & TVs", "unit_cost": 85000.00, "stock_quantity": 42},
    {"name": "50-Inch Android Smart TV (Pallet: 4 units)", "sku": "TV-50-ANDP4", "category": "Electronics & TVs", "unit_cost": 172000.00, "stock_quantity": 25},
    {"name": "32-Inch Frameless Digital TV (Pallet: 10 units)", "sku": "TV-32-DGTP10", "category": "Electronics & TVs", "unit_cost": 125000.00, "stock_quantity": 60},
    {"name": "Bluetooth Soundbar + Subwoofer (Carton: 5 units)", "sku": "AUD-SB-SUB5", "category": "Electronics & TVs", "unit_cost": 75000.00, "stock_quantity": 35},

    # --- CATEGORY: HEAVY HOUSEHOLD APPLIANCES ---
    {"name": "Double Door Frost-Free Fridge 400L (Single)", "sku": "APP-FR-DD400", "category": "Heavy Appliances", "unit_cost": 72000.00, "stock_quantity": 28},
    {"name": "Chest Freezer 250L (Single Unit)", "sku": "APP-FZ-CH250", "category": "Heavy Appliances", "unit_cost": 45000.00, "stock_quantity": 40},
    {"name": "Front Load Washing Machine 8KG (Single)", "sku": "APP-WM-FL8K", "category": "Heavy Appliances", "unit_cost": 58000.00, "stock_quantity": 32},
    {"name": "4-Burner Gas Cooker + Electric Oven (Single)", "sku": "APP-CK-4BEO", "category": "Heavy Appliances", "unit_cost": 42000.00, "stock_quantity": 55},

    # --- CATEGORY: AUTOMOTIVE & FLEET VEHICLES ---
    {"name": "1-Ton Commercial Pickup Truck (Single Unit)", "sku": "AUTO-PU-1TON", "category": "Automotive & Fleet", "unit_cost": 3200000.00, "stock_quantity": 8},
    {"name": "Standard Logistics Delivery Van (Single Unit)", "sku": "AUTO-VN-DLV1", "category": "Automotive & Fleet", "unit_cost": 2850000.00, "stock_quantity": 12},
    {"name": "Executive Corporate Sedan (Single Unit)", "sku": "AUTO-SD-EXEC", "category": "Automotive & Fleet", "unit_cost": 4500000.00, "stock_quantity": 4},
    {"name": "Heavy Duty Truck Tires 295/80R22.5 (Set of 6)", "sku": "AUTO-TR-HDT6", "category": "Automotive & Fleet", "unit_cost": 180000.00, "stock_quantity": 30},

    # --- CATEGORY: CONSTRUCTION & BUILDING MATERIALS ---
    {"name": "Portland Cement 50kg (Pallet: 40 Bags)", "sku": "BLD-CM-50K40", "category": "Building Materials", "unit_cost": 34000.00, "stock_quantity": 150},
    {"name": "D12 Ribbed Steel Rebar (Bundle: 50 pcs)", "sku": "BLD-ST-D12B50", "category": "Building Materials", "unit_cost": 48000.00, "stock_quantity": 85},
    {"name": "Corrugated Iron Roofing Sheets (Bundle: 20 pcs)", "sku": "BLD-RF-IRN20", "category": "Building Materials", "unit_cost": 22000.00, "stock_quantity": 110},
    {"name": "Premium White Emulsion Paint (20L Bucket)", "sku": "BLD-PT-WHT20", "category": "Building Materials", "unit_cost": 6500.00, "stock_quantity": 240},
    {"name": "Ceramic Floor Tiles 60x60cm (Pallet: 20 Cartons)", "sku": "BLD-TL-CR60", "category": "Building Materials", "unit_cost": 32000.00, "stock_quantity": 70},

    # --- CATEGORY: OFFICE FURNITURE ---
    {"name": "Ergonomic Mesh Office Chair (Carton: 2 units)", "sku": "FUR-CH-ERG2", "category": "Office Furniture", "unit_cost": 28000.00, "stock_quantity": 65},
    {"name": "Executive Mahogany L-Desk (Single Unit)", "sku": "FUR-DS-EXEC1", "category": "Office Furniture", "unit_cost": 45000.00, "stock_quantity": 20},
    {"name": "4-Drawer Steel Filing Cabinet (Single Unit)", "sku": "FUR-CB-STL4", "category": "Office Furniture", "unit_cost": 22000.00, "stock_quantity": 45}
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
            # Also purge old automated stocking debits so we don't double-charge the ledger!
            db.session.query(Ledger).filter(Ledger.description.like('%Initial Enterprise Warehouse Stocking%')).delete(synchronize_session=False)
            db.session.commit()
            print("[!] Old inventory and automated ledger charges purged successfully.\n")
        except Exception as e:
            print(f"[ERROR] Failed to purge old inventory: {e}")
            db.session.rollback()

        added_count = 0
        total_value = 0.0
        
        # Inject the massive list
        for item in master_b2b_inventory:
            new_product = Product(
                name=item['name'],
                sku=item['sku'],
                category=item['category'],
                unit_cost=item['unit_cost'],
                stock_quantity=item['stock_quantity']
            )
            db.session.add(new_product)
            added_count += 1
            item_total = item['unit_cost'] * item['stock_quantity']
            total_value += item_total
            
            # Terminal output logic
            status = "CRITICAL" if item['stock_quantity'] < 25 else "HEALTHY"
            if item['stock_quantity'] == 0: status = "DEPLETED"
            
            # Formatted terminal output
            print(f"  -> [INJECTED] SKU: {item['sku']:<15} | {item['name'][:35]:<35} | Vol: {item['stock_quantity']:<4} | Status: {status}")
                
        # --- CHARGE THE LEDGER ---
        initial_stock_debit = Ledger(
            transaction_type='Debit',
            amount=total_value,
            description="Initial Enterprise Warehouse Stocking (Bulk B2B Purchase)"
        )
        db.session.add(initial_stock_debit)
        
        db.session.commit()
        
        print("\n" + "="*70)
        print(f"  SYSTEM OVERVIEW: {added_count} active global product lines registered.")
        print(f"  ESTIMATED WAREHOUSE ASSET VALUE: KES {total_value:,.2f}")
        print(f"  CASHBOOK UPDATED: Successfully debited KES {total_value:,.2f} from the master ledger.")
        print("="*70 + "\n")

if __name__ == "__main__":
    seed_database()