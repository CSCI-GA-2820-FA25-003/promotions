## API Reference

**Base URL**: `/`

### Root Endpoint

*   **`GET /`**: Returns service metadata.

    ```json
    {
      "name": "Promotions Service",
      "version": "1.0.0",
      "description": "RESTful service for managing promotions",
      "paths": { "promotions": "/promotions" }
    }
    ```

### `/promotions` Endpoints

#### `GET /promotions`

Lists all promotions or filters them based on query parameters.

*   **Query Parameters (only one is applied, in this priority order):**
    *   `id` (integer)
    *   `name` (string)
    *   `product_id` (integer)
    *   `promotion_type` (string)
*   **Success Response**: `200 OK` with a JSON array of promotion objects.

#### `POST /promotions`

Creates a new promotion.

*   **Request Body**: JSON object with the following fields:
    *   `name` (string, required)
    *   `promotion_type` (string, required)
    *   `value` (integer, required)
    *   `product_id` (integer, required)
    *   `start_date` (string, `YYYY-MM-DD`, required)
    *   `end_date` (string, `YYYY-MM-DD`, required)
*   **Success Response**: `201 Created` with the new promotion object and a `Location` header.

### `/promotions/{id}` Endpoints

#### `GET /promotions/{id}`

Retrieves a single promotion by its ID.

*   **Success Response**: `200 OK` with the promotion object.
*   **Error Response**: `404 Not Found`.

#### `PUT /promotions/{id}`

Updates a promotion. The request body must contain a full promotion object.

*   **Request Body**: Same as `POST /promotions`.
*   **Success Response**: `200 OK` with the updated promotion object.
*   **Error Response**: `404 Not Found`.

#### `DELETE /promotions/{id}`

Deletes a promotion.

*   **Success Response**: `204 No Content`.
*   **Error Response**: `404 Not Found`.

### Common Error Responses

| Status Code | Reason                               |
| ----------- | ------------------------------------ |
| `400`       | Bad Request (e.g., invalid JSON)     |
| `404`       | Not Found                            |
| `405`       | Method Not Allowed                   |
| `415`       | Unsupported Media Type               |
| `500`       | Internal Server Error                |