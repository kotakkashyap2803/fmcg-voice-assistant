
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.retailers.models import Retailer
from apps.catalogue.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductAlias,
    ProductVariant,
)
from apps.schemes.models import Scheme, SchemeSlab


class Command(BaseCommand):
    help = "Creates reusable demo users, retailers, catalogue, inventory and schemes."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Starting demo data setup...")

        user = self.create_demo_user()
        self.create_retailers(user)

        products = self.create_products()
        self.create_schemes(products)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            "Demo data setup completed successfully."
        ))
        self.stdout.write("Demo login:")
        self.stdout.write("  Username: demo_user")
        self.stdout.write("  Password: Demo@12345")
        self.stdout.write("")
        self.stdout.write("Created/updated 5 demo retailers.")
        self.stdout.write("Created/updated 8 demo products.")
        self.stdout.write("Existing inventory quantities were preserved.")

    def create_demo_user(self):
        User = get_user_model()

        user, created = User.objects.get_or_create(
            username="demo_user",
            defaults={
                "email": "demo@example.com",
                "is_active": True,
            },
        )

        if created:
            user.set_password("Demo@12345")
            user.save(update_fields=["password"])
            self.stdout.write("Created demo login user.")
        else:
            self.stdout.write("Demo login user already exists; password unchanged.")

        return user

    def create_retailers(self, user):
        retailers = [
            {
                "retailer_code": "DEMO-RET-001",
                "name": "Rahul Sharma",
                "shop_name": "Sharma General Stores",
                "primary_phone": "9000000001",
                "email": "rahul@example.com",
                "address_line_1": "Shop 1, Main Market",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
                "territory": "Mumbai South",
            },
            {
                "retailer_code": "DEMO-RET-002",
                "name": "Priya Patel",
                "shop_name": "Patel Provision Store",
                "primary_phone": "9000000002",
                "email": "priya@example.com",
                "address_line_1": "Shop 4, Station Road",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400053",
                "territory": "Mumbai West",
            },
            {
                "retailer_code": "DEMO-RET-003",
                "name": "Amit Mehta",
                "shop_name": "Mehta Supermarket",
                "primary_phone": "9000000003",
                "email": "amit@example.com",
                "address_line_1": "12 Market Street",
                "city": "Thane",
                "state": "Maharashtra",
                "pincode": "400601",
                "territory": "Thane",
            },
            {
                "retailer_code": "DEMO-RET-004",
                "name": "Sneha Joshi",
                "shop_name": "Joshi Daily Needs",
                "primary_phone": "9000000004",
                "email": "sneha@example.com",
                "address_line_1": "Shop 2, Central Avenue",
                "city": "Navi Mumbai",
                "state": "Maharashtra",
                "pincode": "400703",
                "territory": "Navi Mumbai",
            },
            {
                "retailer_code": "DEMO-RET-005",
                "name": "Vikram Desai",
                "shop_name": "Desai Wholesale Mart",
                "primary_phone": "9000000005",
                "email": "vikram@example.com",
                "address_line_1": "Warehouse 5, Industrial Area",
                "city": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400072",
                "territory": "Mumbai East",
            },
        ]

        for data in retailers:
            code = data["retailer_code"]

            Retailer.objects.update_or_create(
                retailer_code=code,
                defaults={
                    **data,
                    "retailer_type": Retailer.RetailerType.KIRANA,
                    "business_status": Retailer.BusinessStatus.ACTIVE,
                    "sales_representative": user,
                },
            )

        self.stdout.write("Retailers created/updated.")

    def create_products(self):
        catalogue = [
            {
                "brand": "GoldDrop",
                "category": "Edible Oils",
                "name": "Refined Sunflower Oil",
                "code": "DEMO-GD-SFO",
                "description": "Demo refined sunflower cooking oil.",
                "aliases": [
                    "sunflower oil",
                    "refined sunflower oil",
                    "gold drop oil",
                ],
                "variants": [
                    ("500 ml", "DEMO-GD-SFO-500", "500", "ML", "90", "82", "500"),
                    ("1 litre", "DEMO-GD-SFO-1L", "1", "L", "175", "160", "300"),
                    ("5 litre", "DEMO-GD-SFO-5L", "5", "L", "820", "780", "100"),
                ],
            },
            {
                "brand": "Saffola",
                "category": "Edible Oils",
                "name": "Gold Blended Edible Oil",
                "code": "DEMO-SAF-GOLD",
                "description": "Demo blended edible oil.",
                "aliases": ["saffola oil", "saffola gold"],
                "variants": [
                    ("1 litre", "DEMO-SAF-GOLD-1L", "1", "L", "190", "175", "250"),
                    ("5 litre", "DEMO-SAF-GOLD-5L", "5", "L", "900", "850", "80"),
                ],
            },
            {
                "brand": "Parachute",
                "category": "Hair Care",
                "name": "100% Pure Coconut Oil",
                "code": "DEMO-PAR-COCO",
                "description": "Demo pure coconut hair oil.",
                "aliases": ["coconut oil", "parachute coconut oil"],
                "variants": [
                    ("200 ml", "DEMO-PAR-COCO-200", "200", "ML", "110", "99", "300"),
                    ("500 ml", "DEMO-PAR-COCO-500", "500", "ML", "240", "220", "150"),
                ],
            },
            {
                "brand": "Nihar Naturals",
                "category": "Hair Care",
                "name": "Shanti Amla Hair Oil",
                "code": "DEMO-NIH-AMLA",
                "description": "Demo amla hair oil.",
                "aliases": ["amla oil", "nihar hair oil"],
                "variants": [
                    ("200 ml", "DEMO-NIH-AMLA-200", "200", "ML", "95", "85", "200"),
                ],
            },
            {
                "brand": "Livon",
                "category": "Hair Care",
                "name": "Hair Serum",
                "code": "DEMO-LIV-SERUM",
                "description": "Demo hair serum.",
                "aliases": ["livon serum", "hair serum"],
                "variants": [
                    ("100 ml", "DEMO-LIV-SERUM-100", "100", "ML", "180", "160", "150"),
                ],
            },
            {
                "brand": "Set Wet",
                "category": "Personal Care",
                "name": "Cool Avatar Deodorant",
                "code": "DEMO-SET-DEO",
                "description": "Demo deodorant.",
                "aliases": ["set wet deodorant", "deodorant"],
                "variants": [
                    ("150 ml", "DEMO-SET-DEO-150", "150", "ML", "220", "195", "120"),
                ],
            },
            {
                "brand": "Mediker",
                "category": "Personal Care",
                "name": "Anti-Lice Treatment Shampoo",
                "code": "DEMO-MED-SHAM",
                "description": "Demo anti-lice shampoo.",
                "aliases": ["mediker shampoo", "anti lice shampoo"],
                "variants": [
                    ("50 ml", "DEMO-MED-SHAM-50", "50", "ML", "85", "75", "100"),
                ],
            },
            {
                "brand": "Nihar Naturals",
                "category": "Hair Care",
                "name": "Naturals Coconut Hair Oil",
                "code": "DEMO-NIH-COCO",
                "description": "Demo coconut hair oil.",
                "aliases": ["nihar coconut oil", "coconut hair oil"],
                "variants": [
                    ("200 ml", "DEMO-NIH-COCO-200", "200", "ML", "90", "80", "180"),
                ],
            },
        ]

        created_products = {}

        for item in catalogue:
            brand, _ = Brand.objects.get_or_create(
                name=item["brand"],
                defaults={"is_active": True},
            )

            category, _ = Category.objects.get_or_create(
                name=item["category"],
                defaults={"is_active": True},
            )

            product, _ = Product.objects.update_or_create(
                product_code=item["code"],
                defaults={
                    "name": item["name"],
                    "brand": brand,
                    "category": category,
                    "description": item["description"],
                    "is_active": True,
                },
            )

            for alias in item["aliases"]:
                ProductAlias.objects.update_or_create(
                    alias=alias,
                    defaults={
                        "product": product,
                        "language": "en",
                    },
                )

            variants = {}

            for (
                variant_name,
                sku,
                pack_size,
                unit,
                mrp,
                selling_price,
                stock,
            ) in item["variants"]:

                variant, _ = ProductVariant.objects.update_or_create(
                    sku=sku,
                    defaults={
                        "product": product,
                        "variant_name": variant_name,
                        "pack_size": Decimal(pack_size),
                        "unit": unit,
                        "mrp": Decimal(mrp),
                        "selling_price": Decimal(selling_price),
                        "is_active": True,
                    },
                )

                # Create initial stock only if inventory does not exist.
                # Never overwrite existing stock when this command is rerun.
                Inventory.objects.get_or_create(
                    variant=variant,
                    defaults={
                        "quantity_on_hand": Decimal(stock),
                        "reorder_level": Decimal("10"),
                    },
                )

                variants[sku] = variant

            created_products[item["code"]] = {
                "product": product,
                "variants": variants,
            }

        self.stdout.write("Products, aliases, variants and inventory created/updated.")
        return created_products

    def create_schemes(self, products):
        now = timezone.now()
        start_date = now - timedelta(days=1)
        end_date = now + timedelta(days=365)

        gold_drop_500 = products["DEMO-GD-SFO"]["variants"][
            "DEMO-GD-SFO-500"
        ]

        parachute_200 = products["DEMO-PAR-COCO"]["variants"][
            "DEMO-PAR-COCO-200"
        ]

        livon_100 = products["DEMO-LIV-SERUM"]["variants"][
            "DEMO-LIV-SERUM-100"
        ]

        schemes = [
            {
                "scheme_code": "DEMO-GD-SLAB-05",
                "name": "GoldDrop Sunflower Oil Quantity Slab",
                "description": "Get 5% off when ordering 10 or more 500 ml packs.",
                "scheme_type": Scheme.SchemeType.QUANTITY_SLAB,
                "variant": gold_drop_500,
                "min_quantity": 10,
                "discount_percentage": None,
                "buy_quantity": None,
                "free_quantity": None,
                "slabs": [
                    {
                        "min_quantity": 10,
                        "max_quantity": None,
                        "discount_percentage": Decimal("5.00"),
                    },
                ],
            },
            {
                "scheme_code": "DEMO-PAR-BXGY",
                "name": "Parachute Buy 5 Get 1 Free",
                "description": "Buy 5 packs of 200 ml and get 1 free.",
                "scheme_type": Scheme.SchemeType.BUY_X_GET_Y,
                "variant": parachute_200,
                "min_quantity": 5,
                "discount_percentage": None,
                "buy_quantity": 5,
                "free_quantity": 1,
                "slabs": [],
            },
            {
                "scheme_code": "DEMO-LIV-PCT10",
                "name": "Livon Hair Serum 10 Percent Discount",
                "description": "Get 10% off on Livon Hair Serum 100 ml.",
                "scheme_type": Scheme.SchemeType.PERCENTAGE,
                "variant": livon_100,
                "min_quantity": 1,
                "discount_percentage": Decimal("10.00"),
                "buy_quantity": None,
                "free_quantity": None,
                "slabs": [],
            },
        ]

        for item in schemes:
            scheme, _ = Scheme.objects.update_or_create(
                scheme_code=item["scheme_code"],
                defaults={
                    "name": item["name"],
                    "description": item["description"],
                    "scheme_type": item["scheme_type"],
                    "min_quantity": item["min_quantity"],
                    "discount_percentage": item["discount_percentage"],
                    "buy_quantity": item["buy_quantity"],
                    "free_quantity": item["free_quantity"],
                    "start_date": start_date,
                    "end_date": end_date,
                    "is_active": True,
                    "is_combinable": False,
                },
            )

            scheme.applicable_variants.set([item["variant"]])

            for slab in item["slabs"]:
                SchemeSlab.objects.update_or_create(
                    scheme=scheme,
                    min_quantity=slab["min_quantity"],
                    defaults={
                        "max_quantity": slab["max_quantity"],
                        "discount_percentage": slab["discount_percentage"],
                    },
                )

        self.stdout.write("Three demo schemes created/updated.")
