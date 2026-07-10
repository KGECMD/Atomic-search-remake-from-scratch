# Atomic Search API Documentation

## Overview
Atomic Search provides a REST API for programmatic search access.

## Base URL
```
https://your-instance.com/api/v1
```

## Authentication
Include API key in `X-API-Key` header.

## Endpoints

### GET /api/v1/search
Perform a search.
- q: Search query (required)
- type: web, images, videos, news, shopping
- page: Page number
- limit: Results per page (max 100)

### GET /api/v1/suggestions
Get search suggestions.

### POST /api/v1/vote
Vote on search results.

### GET/POST/DELETE /api/v1/bookmarks
Manage bookmarks.

### GET/POST /api/v1/collections
Manage collections.

### POST /api/v1/ai/summarize
Get AI summary of results.

### POST /api/v1/ai/chat
Chat with AI assistant.

## Error Codes
- 400: Bad Request
- 401: Unauthorized
- 403: Forbidden
- 404: Not Found
- 429: Rate Limited
- 500: Server Error
