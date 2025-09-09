#!/bin/bash

echo "=== PHASE 3 TESTING SCRIPT ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8001"

# Step 1: Check backend health
echo -e "${YELLOW}1. Testing Backend Health...${NC}"
curl -s $BASE_URL/health | jq
echo ""

# Step 2: Get a token (you need to login via CLI first)
echo -e "${YELLOW}2. Checking for saved auth token...${NC}"
CONFIG_FILE="$HOME/.config/secret-cli/config.json"
if [ -f "$CONFIG_FILE" ]; then
    TOKEN=$(cat $CONFIG_FILE | jq -r '.token')
    USER_NAME=$(cat $CONFIG_FILE | jq -r '.user.name // .user.login')
    echo -e "${GREEN}Found token for user: $USER_NAME${NC}"
else
    echo -e "${RED}No saved auth found. Please run the CLI and login first:${NC}"
    echo "cd cli && npm run dev"
    echo "Then select 'Login with GitHub'"
    exit 1
fi
echo ""

# Step 3: Test Team Endpoints
echo -e "${YELLOW}3. Testing Team Endpoints...${NC}"

echo "3a. List all teams in organization:"
curl -s -H "Authorization: Bearer $TOKEN" $BASE_URL/teams | jq
echo ""

echo "3b. List my teams:"
curl -s -H "Authorization: Bearer $TOKEN" $BASE_URL/teams/mine | jq
echo ""

echo "3c. List all users in organization:"
curl -s -H "Authorization: Bearer $TOKEN" $BASE_URL/users | jq
echo ""

# Step 4: Test Enhanced Secrets Endpoint
echo -e "${YELLOW}4. Testing Enhanced Secrets Endpoint...${NC}"
echo "Getting secrets with detailed sharing info:"
curl -s -H "Authorization: Bearer $TOKEN" $BASE_URL/secrets | jq
echo ""

# Step 5: Create a test team (if user is admin)
echo -e "${YELLOW}5. Attempting to create a test team (admin only)...${NC}"
TEAM_RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    "$BASE_URL/teams?name=TestTeam$(date +%s)")
    
if echo "$TEAM_RESPONSE" | jq -e '.team' > /dev/null 2>&1; then
    TEAM_ID=$(echo "$TEAM_RESPONSE" | jq -r '.team.id')
    echo -e "${GREEN}Created team with ID: $TEAM_ID${NC}"
    echo "$TEAM_RESPONSE" | jq
    
    # Get team members
    echo ""
    echo "5a. Getting team members:"
    curl -s -H "Authorization: Bearer $TOKEN" $BASE_URL/teams/$TEAM_ID/members | jq
else
    echo -e "${RED}Could not create team (not admin or error)${NC}"
    echo "$TEAM_RESPONSE" | jq
fi
echo ""

# Step 6: Create a test secret with ACL
echo -e "${YELLOW}6. Creating a test secret with permissions...${NC}"
SECRET_RESPONSE=$(curl -s -X POST -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "key": "test-secret-'$(date +%s)'",
        "value": "secret-value-123",
        "acl_entries": [
            {
                "subject_type": "org",
                "subject_id": null,
                "can_read": true,
                "can_write": false
            }
        ]
    }' \
    $BASE_URL/secrets)

if echo "$SECRET_RESPONSE" | jq -e '.id' > /dev/null 2>&1; then
    echo -e "${GREEN}Created secret successfully${NC}"
    echo "$SECRET_RESPONSE" | jq
else
    echo -e "${RED}Failed to create secret${NC}"
    echo "$SECRET_RESPONSE" | jq
fi
echo ""

# Step 7: Check enhanced secret data
echo -e "${YELLOW}7. Checking enhanced secret data structure...${NC}"
SECRETS=$(curl -s -H "Authorization: Bearer $TOKEN" $BASE_URL/secrets)
echo "First secret with enhanced data:"
echo "$SECRETS" | jq '.[0] | {
    key: .key,
    created_by_name: .created_by_name,
    is_creator: .is_creator,
    can_write: .can_write,
    shared_with: .shared_with
}'
echo ""

echo -e "${GREEN}=== PHASE 3 BACKEND TESTING COMPLETE ===${NC}"
echo ""
echo "Next steps:"
echo "1. Run the CLI: cd cli && npm run dev"
echo "2. Check 'View Teams' menu option"
echo "3. Check 'View Secrets' for new sharing indicators"