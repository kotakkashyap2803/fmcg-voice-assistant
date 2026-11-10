from django.db import models

# Create your models here.
from django.db import models
from django.conf import settings


class Retailer(models.Model):

    class RetailerType(models.TextChoices):
        KIRANA = "KIRANA", "Kirana Store"
        SUPERMARKET = "SUPERMARKET", "Supermarket"
        WHOLESALER = "WHOLESALER", "Wholesaler"
        DISTRIBUTOR = "DISTRIBUTOR", "Distributor"
        OTHER = "OTHER", "Other"

    class BusinessStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"
        BLOCKED = "BLOCKED", "Blocked"

    name = models.CharField(max_length=200)

    shop_name = models.CharField(max_length=200)

    retailer_code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True
    )

    retailer_type = models.CharField(
        max_length=20,
        choices=RetailerType.choices,
        default=RetailerType.KIRANA
    )

    primary_phone = models.CharField(
        max_length=20,
        db_index=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    address_line_1 = models.CharField(max_length=255)

    address_line_2 = models.CharField(
        max_length=255,
        blank=True
    )

    city = models.CharField(max_length=100)

    state = models.CharField(max_length=100)

    pincode = models.CharField(max_length=10)

    territory = models.CharField(
        max_length=100,
        db_index=True
    )

    sales_representative = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_retailers"
    )

    business_status = models.CharField(
        max_length=20,
        choices=BusinessStatus.choices,
        default=BusinessStatus.ACTIVE,
        db_index=True
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "retailers"
        ordering = ["name"]
        indexes = [
            models.Index(
                fields=["territory", "business_status"],
                name="retailer_territory_status_idx"
            ),
            models.Index(
                fields=["name", "shop_name"],
                name="retailer_name_shop_idx"
            ),
        ]

    def __str__(self):
        return f"{self.shop_name} ({self.retailer_code})"


class RetailerContact(models.Model):

    class ContactType(models.TextChoices):
        OWNER = "OWNER", "Owner"
        MANAGER = "MANAGER", "Manager"
        STAFF = "STAFF", "Staff"
        OTHER = "OTHER", "Other"

    retailer = models.ForeignKey(
        Retailer,
        on_delete=models.CASCADE,
        related_name="contacts"
    )

    name = models.CharField(max_length=150)

    phone = models.CharField(
        max_length=20,
        db_index=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    contact_type = models.CharField(
        max_length=20,
        choices=ContactType.choices,
        default=ContactType.OWNER
    )

    is_primary = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "retailer_contacts"
        ordering = ["-is_primary", "name"]
        indexes = [
            models.Index(
                fields=["retailer", "is_primary"],
                name="retailer_contact_primary_idx"
            )
        ]

    def __str__(self):
        return f"{self.name} - {self.phone}"