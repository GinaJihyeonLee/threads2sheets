#!/bin/bash

# Set the working directory
cd /path/to/threads2sheets

# Set environment variables (replace with your actual values)
ACCESS_TOKEN="<YOUR_ACCESS_TOKEN>"
CREDS_JSON="/path/to/credentials.json"
SPREADSHEET_ID="<YOUR_SPREADSHEET_ID>"
WORKSHEET_NAME="<YOUR_WORKSHEET_NAME>"

# Calculate date range (last 7 days)
SINCE=$(date -v-7d +%Y-%m-%d)
# UNTIL=$(date +%Y-%m-%d)  # Optional: uncomment if you want to specify end date

# Log file
LOG_FILE="/path/to/threads2sheets/logs/threads_update_$(date +%Y%m%d_%H%M%S).log"
mkdir -p /path/to/threads2sheets/logs

# Run the Python script
echo "Starting Threads update at $(date)" >> "$LOG_FILE"
/usr/bin/python3 /path/to/threads2sheets/threads_to_sheets.py \
    --access-token "$ACCESS_TOKEN" \
    --creds-json "$CREDS_JSON" \
    --spreadsheet-id "$SPREADSHEET_ID" \
    --worksheet "$WORKSHEET_NAME" \
    --since "$SINCE" >> "$LOG_FILE" 2>&1
    # --until "$UNTIL" \  # Optional: uncomment if using end date
    # --limit 100  # Optional: uncomment to set a limit

echo "Threads update completed at $(date)" >> "$LOG_FILE"