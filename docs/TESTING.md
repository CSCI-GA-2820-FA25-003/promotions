## Testing & Quality

Run the full suite (unit + integration):

```bash
make test
```

Coverage gate is **≥ 95%**. The suite includes:

* Model CRUD, serialization/deserialization, and transaction rollback tests
* Query tests for `find`, `find_by_name`, `find_by_product_id`, `find_by_promotion_type`
* Route tests for all filters (`id`, `name`, `product_id`, `promotion_type`) and “no filter”
* Error‑path tests for 400/404/405/415 and a simulated 500 path (with temporary disabling of exception propagation to hit the JSON 500 handler)
