def get_openapi_spec():
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "GrandView Hotel Management & Reservation API",
            "version": "1.0.0",
            "description": "Production REST API powering both the modern React Single Page Application and external PMS integrations."
        },
        "servers": [{"url": "http://127.0.0.1:8000"}],
        "paths": {
            "/api/v1/rooms/": {
                "get": {"summary": "List active room types", "responses": {"200": {"description": "List of room types"}}}
            },
            "/api/v1/availability/": {
                "get": {
                    "summary": "Query room availability for date range",
                    "parameters": [
                        {"name": "check_in", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "check_out", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "guests", "in": "query", "required": False, "schema": {"type": "integer"}}
                    ],
                    "responses": {"200": {"description": "Available rooms and pricing"}}
                }
            },
            "/api/v1/holds/": {
                "post": {
                    "summary": "Place a 15-minute temporary hold",
                    "responses": {"201": {"description": "Hold created"}, "409": {"description": "Conflict"}}
                }
            },
            "/api/v1/bookings/": {
                "post": {
                    "summary": "Confirm reservation",
                    "responses": {"201": {"description": "Confirmed"}, "409": {"description": "Conflict"}}
                }
            },
            "/api/v1/reservations/": {
                "get": {"summary": "Query reservations list", "responses": {"200": {"description": "Reservations"}}}
            },
            "/api/v1/inventory/": {
                "get": {"summary": "Query physical room inventory", "responses": {"200": {"description": "Inventory"}}}
            },
            "/api/v1/reports/operations/": {
                "get": {"summary": "Retrieve operations analytics", "responses": {"200": {"description": "Analytics"}}}
            }
        }
    }
