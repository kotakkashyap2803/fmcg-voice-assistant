from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import (
    Avg,
    Count,
    Sum,
    F,
    Q,
)
from django.utils import timezone

from apps.retailers.models import Retailer
from apps.orders.models import Order, OrderItem
from apps.conversations.models import Conversation, ConversationMessage
from apps.followups.models import FollowUp


class AnalyticsService:
    """
    Provides business analytics using existing transactional records.

    No analytics data is duplicated or stored separately.
    """

    @staticmethod
    def _apply_date_filter(queryset, field, start_date, end_date):
        current_tz = timezone.get_current_timezone()

        if start_date:
            start_datetime = timezone.make_aware(
                datetime.combine(start_date, time.min),
                current_tz
            )

            queryset = queryset.filter(
                **{f"{field}__gte": start_datetime}
            )

        if end_date:
            end_datetime = timezone.make_aware(
                datetime.combine(
                    end_date + timedelta(days=1),
                    time.min
                ),
                current_tz
            )

            queryset = queryset.filter(
                **{f"{field}__lt": end_datetime}
            )

        return queryset

    @staticmethod
    def _money(value):
        amount = value if value is not None else Decimal("0.00")
        return str(Decimal(amount).quantize(Decimal("0.01")))

    @classmethod
    def get_dashboard(cls, start_date=None, end_date=None):

        today = timezone.localdate()

        # Default reporting period: last 30 days, including today.
        if not start_date and not end_date:
            start_date = today - timedelta(days=29)
            end_date = today

        # --------------------------------------------------
        # 1. Retailer KPIs
        # --------------------------------------------------

        total_retailers = Retailer.objects.count()

        active_retailers = Retailer.objects.filter(
            business_status=Retailer.BusinessStatus.ACTIVE
        ).count()

        inactive_retailers = Retailer.objects.filter(
            business_status=Retailer.BusinessStatus.INACTIVE
        ).count()

        blocked_retailers = Retailer.objects.filter(
            business_status=Retailer.BusinessStatus.BLOCKED
        ).count()

        # --------------------------------------------------
        # 2. Order KPIs
        # --------------------------------------------------

        orders = cls._apply_date_filter(
            Order.objects.all(),
            "created_at",
            start_date,
            end_date
        )

        confirmed_orders = orders.filter(
            status=Order.Status.CONFIRMED
        )

        cancelled_orders = orders.filter(
            status=Order.Status.CANCELLED
        )

        draft_orders = orders.filter(
            status=Order.Status.DRAFT
        )

        confirmed_sales = cls._apply_date_filter(
            Order.objects.filter(
                status=Order.Status.CONFIRMED,
                confirmed_at__isnull=False
            ),
            "confirmed_at",
            start_date,
            end_date
        )

        order_count = orders.count()
        confirmed_count = confirmed_orders.count()

        sales_summary = confirmed_sales.aggregate(
            revenue=Sum("total_amount"),
            subtotal=Sum("subtotal"),
            discount=Sum("discount_amount"),
            average_order_value=Avg("total_amount")
        )

        revenue = sales_summary["revenue"] or Decimal("0.00")

        average_order_value = (
            sales_summary["average_order_value"]
            or Decimal("0.00")
        )

        # --------------------------------------------------
        # 3. Conversation KPIs
        # --------------------------------------------------

        conversations = cls._apply_date_filter(
            Conversation.objects.all(),
            "started_at",
            start_date,
            end_date
        )

        conversation_summary = conversations.aggregate(
            total=Count("id"),
            completed=Count(
                "id",
                filter=Q(status=Conversation.Status.COMPLETED)
            ),
            failed=Count(
                "id",
                filter=Q(status=Conversation.Status.FAILED)
            ),
            active=Count(
                "id",
                filter=Q(status=Conversation.Status.ACTIVE)
            )
        )

        outcome_distribution = list(
            conversations.values("outcome")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        language_distribution = list(
            conversations.values("language")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        channel_distribution = list(
            conversations.values("channel")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # --------------------------------------------------
        # 4. Intent distribution
        # --------------------------------------------------

        # messages = cls._apply_date_filter(
        #     ConversationMessage.objects.filter(
        #         intent__gt=""
        #     ),
        #     "created_at",
        #     start_date,
        #     end_date
        # )

        # intent_distribution = list(
        #     messages.values("intent")
        #     .annotate(count=Count("id"))
        #     .order_by("-count")
        # )

        # --------------------------------------------------
        # 4. Retailer intent distribution
        # --------------------------------------------------

        messages = cls._apply_date_filter(
            ConversationMessage.objects.filter(
                intent__gt="",
                speaker="RETAILER"
            ),
            "created_at",
            start_date,
            end_date
        )

        intent_distribution = list(
            messages.values("intent")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # --------------------------------------------------
        # 5. Follow-up KPIs
        # --------------------------------------------------

        # followups = cls._apply_date_filter(
        #     FollowUp.objects.all(),
        #     "due_at",
        #     start_date,
        #     end_date
        # )

        # current_time = timezone.now()

        # followup_summary = followups.aggregate(
        #     total=Count("id"),
        #     pending=Count(
        #         "id",
        #         filter=Q(status=FollowUp.Status.PENDING)
        #     ),
        #     completed=Count(
        #         "id",
        #         filter=Q(status=FollowUp.Status.COMPLETED)
        #     ),
        #     cancelled=Count(
        #         "id",
        #         filter=Q(status=FollowUp.Status.CANCELLED)
        #     ),
        #     overdue=Count(
        #         "id",
        #         filter=(
        #             Q(status=FollowUp.Status.OVERDUE)
        #             | Q(
        #                 status=FollowUp.Status.PENDING,
        #                 due_at__lt=current_time
        #             )
        #         )
        #     )
        # )

                # --------------------------------------------------
        # 5. Follow-up KPIs
        # --------------------------------------------------

        followups = cls._apply_date_filter(
            FollowUp.objects.all(),
            "created_at",
            start_date,
            end_date
        )

        current_time = timezone.now()

        followup_summary = followups.aggregate(
            total=Count("id"),
            pending=Count(
                "id",
                filter=Q(status=FollowUp.Status.PENDING)
            ),
            completed=Count(
                "id",
                filter=Q(status=FollowUp.Status.COMPLETED)
            ),
            cancelled=Count(
                "id",
                filter=Q(status=FollowUp.Status.CANCELLED)
            ),
            overdue=Count(
                "id",
                filter=(
                    Q(status=FollowUp.Status.OVERDUE)
                    | Q(
                        status=FollowUp.Status.PENDING,
                        due_at__lt=current_time
                    )
                )
            )
        )

        # # --------------------------------------------------
        # # 6. Daily confirmed sales
        # # --------------------------------------------------

        # daily_sales = list(
        #     confirmed_sales
        #     .annotate(
        #         sales_date=TruncDate("confirmed_at")
        #     )
        #     .values("sales_date")
        #     .annotate(
        #         order_count=Count("id"),
        #         revenue=Sum("total_amount")
        #     )
        #     .order_by("sales_date")
        # )

        # for item in daily_sales:
        #     item["sales_date"] = item["sales_date"].isoformat()
        #     item["revenue"] = cls._money(item["revenue"])

                # --------------------------------------------------
        # 6. Daily sales trend
        # --------------------------------------------------

        daily_sales_map = {}

        daily_sales_records = confirmed_sales.order_by(
            "confirmed_at"
        ).values(
            "confirmed_at",
            "total_amount"
        )

        for record in daily_sales_records:
            local_datetime = timezone.localtime(record["confirmed_at"])
            sales_date = local_datetime.date().isoformat()

            if sales_date not in daily_sales_map:
                daily_sales_map[sales_date] = {
                    "sales_date": sales_date,
                    "order_count": 0,
                    "revenue": Decimal("0.00")
                }

            daily_sales_map[sales_date]["order_count"] += 1
            daily_sales_map[sales_date]["revenue"] += (
                record["total_amount"] or Decimal("0.00")
            )

        daily_sales = []

        for item in daily_sales_map.values():
            daily_sales.append({
                "sales_date": item["sales_date"],
                "order_count": item["order_count"],
                "revenue": cls._money(item["revenue"])
            })

        # --------------------------------------------------
        # 7. Top-selling products
        # --------------------------------------------------

        confirmed_items = OrderItem.objects.filter(
            order__in=confirmed_sales
        )

        top_products = list(
            confirmed_items
            .values("product_name", "variant_name")
            .annotate(
                units_sold=Sum("quantity"),
                free_units=Sum("free_quantity"),
                revenue=Sum("total_amount"),
                order_count=Count("order", distinct=True)
            )
            .order_by("-units_sold")[:10]
        )

        for item in top_products:
            item["units_sold"] = str(item["units_sold"] or 0)
            item["free_units"] = str(item["free_units"] or 0)
            item["revenue"] = cls._money(item["revenue"])

        # --------------------------------------------------
        # 8. Top retailers by confirmed revenue
        # --------------------------------------------------

        top_retailers = list(
            confirmed_sales
            .values(
                "retailer_id",
                "retailer__name",
                "retailer__shop_name"
            )
            .annotate(
                order_count=Count("id"),
                revenue=Sum("total_amount")
            )
            .order_by("-revenue")[:10]
        )

        for item in top_retailers:
            item["revenue"] = cls._money(item["revenue"])

        # --------------------------------------------------
        # 9. Final dashboard response
        # --------------------------------------------------

        return {
            "period": {
                "start_date": (
                    start_date.isoformat() if start_date else None
                ),
                "end_date": (
                    end_date.isoformat() if end_date else None
                )
            },

            "retailers": {
                "total": total_retailers,
                "active": active_retailers,
                "inactive": inactive_retailers,
                "blocked": blocked_retailers
            },

            "orders": {
                "total": order_count,
                "confirmed": confirmed_count,
                "draft": draft_orders.count(),
                "cancelled": cancelled_orders.count(),
                "revenue": cls._money(revenue),
                "subtotal": cls._money(sales_summary["subtotal"]),
                "discount": cls._money(sales_summary["discount"]),
                "average_order_value": cls._money(
                    average_order_value
                )
            },

            "conversations": conversation_summary,

            "conversation_outcomes": outcome_distribution,
            "language_distribution": language_distribution,
            "channel_distribution": channel_distribution,
            "intent_distribution": intent_distribution,

            "followups": followup_summary,

            "daily_sales": daily_sales,

            "top_products": top_products,

            "top_retailers": top_retailers
        }