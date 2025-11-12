## Architecture

* **Framework:** Flask
* **ORM:** Flask‑SQLAlchemy
* **Database:** PostgreSQL (psycopg driver)
* **Model:** `Promotion` with auditing fields (`created_at`, `last_updated`) stored server‑side; the REST API’s JSON only exposes core business fields.

---

## Data Model

`Promotion` JSON shape (fields exposed by the API):

| Field            | Type             | Required | Description                             |
| ---------------- | ---------------- | -------- | --------------------------------------- |
| `id`             | integer          | auto     | Primary key                             |
| `name`           | string (≤ 63)    | yes      | Promotion name                          |
| `promotion_type` | string (≤ 63)    | yes      | Free‑form type (e.g., “Percentage off”) |
| `value`          | integer          | yes      | Discount amount/percent (integer)       |
| `product_id`     | integer          | yes      | Associated product identifier           |
| `start_date`     | ISO date (Y‑M‑D) | yes      | Start date, e.g., `"2025-10-01"`        |
| `end_date`       | ISO date (Y‑M‑D) | yes      | End date, e.g., `"2025-10-31"`          |

**Example JSON:**

```json
{
  "id": 1,
  "name": "Summer Sale",
  "promotion_type": "Percentage off",
  "value": 25,
  "product_id": 123,
  "start_date": "2025-06-01",
  "end_date": "2025-06-30"
}
```

> The model also maintains auditing fields (`created_at`, `last_updated`) that are **not** part of the REST JSON.
