#!/bin/bash
# SuperNova Search - Test Script

echo "=========================================="
echo "  SuperNova Search - Test Suite"
echo "=========================================="
echo ""

BASE_URL="${1:-http://localhost:8080}"

echo "Testing: $BASE_URL"
echo ""

# Test 1: Health
echo -n "1. Health Check... "
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo "✓ PASS"
else
    echo "✗ FAIL: $HEALTH"
fi

# Test 2: Stats
echo -n "2. Voting Stats... "
STATS=$(curl -s "$BASE_URL/api/v1/stats")
if echo "$STATS" | grep -q "votes"; then
    echo "✓ PASS"
else
    echo "✗ FAIL: $STATS"
fi

# Test 3: Trending
echo -n "3. Trending Searches... "
TRENDING=$(curl -s "$BASE_URL/api/v1/search/trending")
if echo "$TRENDING" | grep -q "trending"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# Test 4: Operators
echo -n "4. Search Operators... "
OPS=$(curl -s "$BASE_URL/api/v1/search/operators")
if echo "$OPS" | grep -q "examples"; then
    echo "✓ PASS"
else
    echo "✗ FAIL"
fi

# Test 5: Calculator
echo -n "5. Calculator (2+2)... "
CALC=$(curl -s -X POST "$BASE_URL/tools/calculate" \
    -H "Content-Type: application/json" \
    -d '{"expression":"2+2"}')
if echo "$CALC" | grep -q '"result":4'; then
    echo "✓ PASS"
else
    echo "✗ FAIL: $CALC"
fi

# Test 6: Unit Converter
echo -n "6. Unit Converter (1km to m)... "
CONV=$(curl -s -X POST "$BASE_URL/tools/convert" \
    -H "Content-Type: application/json" \
    -d '{"value":1,"from":"km","to":"m","type":"length"}')
if echo "$CONV" | grep -q '"result":1000'; then
    echo "✓ PASS"
else
    echo "✗ FAIL: $CONV"
fi

# Test 7: Currency
echo -n "7. Currency (100USD to EUR)... "
CURR=$(curl -s -X POST "$BASE_URL/tools/currency" \
    -H "Content-Type: application/json" \
    -d '{"amount":100,"from":"USD","to":"EUR"}')
if echo "$CURR" | grep -q "result"; then
    echo "✓ PASS"
else
    echo "✗ FAIL: $CURR"
fi

echo ""
echo "=========================================="
echo "  Test Complete!"
echo "=========================================="
