
import api from "./api";

export interface DashboardAnalytics {
    period: {
        start_date: string;
        end_date: string;
    };
    retailers: {
        total: number;
        active: number;
        inactive: number;
        blocked: number;
    };
    orders: {
        total: number;
        confirmed: number;
        draft: number;
        cancelled: number;
        revenue: string;
        subtotal: string;
        discount: string;
        average_order_value: string;
    };
    conversations: {
        total: number;
        completed: number;
        failed: number;
        active: number;
    };
    conversation_outcomes: {
        outcome: string;
        count: number;
    }[];
    language_distribution: {
        language: string;
        count: number;
    }[];
    channel_distribution: {
        channel: string;
        count: number;
    }[];
    intent_distribution: {
        intent: string;
        count: number;
    }[];
    followups: {
        total: number;
        pending: number;
        completed: number;
        cancelled: number;
        overdue: number;
    };
    daily_sales: {
        sales_date: string;
        order_count: number;
        revenue: string;
    }[];
    top_products: {
        product_name: string;
        variant_name: string;
        units_sold: string;
        free_units: string;
        revenue: string;
        order_count: number;
    }[];
    top_retailers: {
        retailer_id: number;
        retailer__name: string;
        retailer__shop_name: string;
        order_count: number;
        revenue: string;
    }[];
}

interface DashboardAnalyticsResponse {
    success: boolean;
    message: string;
    data: DashboardAnalytics;
}

export async function getDashboardAnalytics(
    startDate: string,
    endDate: string
): Promise<DashboardAnalytics> {
    const response = await api.get<DashboardAnalyticsResponse>(
        "/analytics/dashboard/",
        {
            params: {
                start_date: startDate,
                end_date: endDate,
            },
        }
    );

    if (!response.data.success) {
        throw new Error(
            response.data.message || "Unable to load dashboard analytics."
        );
    }

    return response.data.data;
}
