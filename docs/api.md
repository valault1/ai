# API Documentation

## GET /api/example-items
Returns all items.
**Response:** `GetExampleItemsResponse` (see shared/src/types/api.ts)

## POST /api/example-items
Creates a new item.
**Request:** `CreateExampleItemRequest`
**Response:** `CreateExampleItemResponse` (201)
**Errors:** 400 if `name` is missing

## GET /api/stocks/history
Returns historical daily stock data.
**QueryParams:** `symbol`, `start`, `end`
**Response:** `GetStockHistoryResponse` (see shared/src/types/api.ts)
**Errors:** 400 if params are missing
