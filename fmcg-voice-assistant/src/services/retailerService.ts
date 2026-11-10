
import api from "./api";

export interface Retailer {
    id: number;
    retailer_code: string;
    name: string;
    shop_name: string;
    retailer_type: string;
    primary_phone: string;
    city: string;
    territory: string;
    sales_representative_name: string;
    business_status: string;
}

interface RetailerApiResponse {
    count: number;
    next: string | null;
    previous: string | null;
    results: {
        success: boolean;
        message: string;
        data: Retailer[];
    };
}

export async function getRetailers(): Promise<Retailer[]> {
    const response = await api.get<RetailerApiResponse>("/retailers/");

    if (!response.data.results.success) {
        throw new Error(
            response.data.results.message || "Unable to retrieve retailers."
        );
    }

    return response.data.results.data;
}
