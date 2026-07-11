#!/bin/bash
# SuperNova Search - Build Script

set -e

echo "=========================================="
echo "  SuperNova Search Build Script"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t supernova-search .

echo ""
echo -e "${GREEN}Build successful!${NC}"
echo ""
echo "To run:"
echo "  docker run -p 8080:8080 supernova-search"
echo ""
echo "To deploy on Railway/Render, push to GitHub master branch."
