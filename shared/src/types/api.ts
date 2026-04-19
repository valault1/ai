// shared/src/types/api.ts

import type { ExampleItem } from './models';

export interface GetExampleItemsResponse {
  items: ExampleItem[];
  total: number;
}

export interface CreateExampleItemRequest {
  name: string;
  description?: string;
}

export interface CreateExampleItemResponse {
  item: ExampleItem;
}

export interface StockHistoryPoint {
  time: string; // YYYY-MM-DD
  value: number; // Closing price
}

export interface GetStockHistoryResponse {
  symbol: string;
  data: StockHistoryPoint[];
}
