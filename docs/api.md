# API Documentation

ReUptime provides a comprehensive RESTful API for managing hosts, retrieving metrics, and controlling the monitoring daemon.

## Authentication

Currently, the API does not require authentication. If deploying in a production environment, it's recommended to implement authentication or restrict access using a reverse proxy.

## Host Management

### List All Hosts

**Endpoint**: `GET /api/hosts`

**Response**:
```json
{
  "hosts": [
    {
      "id": 1,
      "name": "Example Server",
      "address": "example.com",
      "is_active": 1,
      "last_check": "2023-06-15 14:30:22",
      "created": "2023-06-01 10:00:00"
    },
    ...
  ]
}
```

### Get Host Details

**Endpoint**: `GET /api/hosts/<host_id>`

**Response**:
```json
{
  "id": 1,
  "name": "Example Server",
  "address": "example.com",
  "is_active": 1,
  "last_check": "2023-06-15 14:30:22",
  "created": "2023-06-01 10:00:00"
}
```

### Add New Host

**Endpoint**: `POST /api/hosts`

**Request Body**:
```json
{
  "name": "New Server",
  "address": "newserver.com"
}
```

**Response**:
```json
{
  "success": true,
  "host": {
    "id": 2,
    "name": "New Server",
    "address": "newserver.com",
    "is_active": 1,
    "created": "2023-06-15 15:00:00"
  }
}
```

### Update Host

**Endpoint**: `PUT /api/hosts/<host_id>`

**Request Body**:
```json
{
  "name": "Updated Server Name",
  "address": "updatedserver.com"
}
```

**Response**:
```json
{
  "success": true,
  "host": {
    "id": 1,
    "name": "Updated Server Name",
    "address": "updatedserver.com",
    "is_active": 1,
    "last_check": "2023-06-15 14:30:22",
    "created": "2023-06-01 10:00:00"
  }
}
```

### Delete Host

**Endpoint**: `DELETE /api/hosts/<host_id>`

**Response**:
```json
{
  "success": true,
  "message": "Host deleted successfully"
}
```

## Metrics

### Get Host Metrics

**Endpoint**: `GET /api/metrics/<host_id>`

**Query Parameters**:
- `range`: Time range for metrics (e.g., `1h`, `24h`, `7d`, `30d`)

**Response**:
```json
{
  "labels": ["2023-06-15 13:00:00", "2023-06-15 13:05:00", ...],
  "datasets": [
    {
      "label": "Uptime",
      "data": [1, 1, 1, 0, 1, ...],
      "borderColor": "rgba(75, 192, 192, 1)",
      "fill": false
    },
    {
      "label": "Latency (ms)",
      "data": [12.5, 13.2, 11.8, null, 14.1, ...],
      "borderColor": "rgba(153, 102, 255, 1)",
      "fill": false
    }
  ]
}
```

## Daemon Management

### Get Daemon Status

**Endpoint**: `GET /api/daemon/status`

**Response**:
```json
{
  "status": "running",
  "pid": 12345,
  "message": "Daemon running normally",
  "interval": 60,
  "last_check": "2023-06-15 15:10:00",
  "last_update": "2023-06-15 15:10:00 EDT"
}
```

### Start Daemon

**Endpoint**: `POST /api/daemon/start`

**Response**:
```json
{
  "success": true,
  "message": "Daemon started successfully"
}
```

### Stop Daemon

**Endpoint**: `POST /api/daemon/stop`

**Response**:
```json
{
  "success": true,
  "message": "Daemon stopped successfully"
}
```

## Error Responses

All API endpoints return appropriate HTTP status codes and error messages in case of failure:

```json
{
  "error": "Error message describing what went wrong"
}
```

Common status codes:
- `400 Bad Request`: Invalid input parameters
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error 