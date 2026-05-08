#!/bin/bash

# --- CONFIGURATION ---
# Replace with your actual Instance ID
INSTANCE_ID="i-020b6ffa22e32cd83"

echo "-----------------------------------------------"
echo "Step 1: Verifying AWS Authentication..."
aws sts get-caller-identity > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "Successfully authenticated."
else
    echo "Error: Not authenticated. Check your 'aws configure' settings."
    exit 1
fi

echo "-----------------------------------------------"
echo "Step 2: Sending Stop Command to $INSTANCE_ID..."
aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --output json

if [ $? -ne 0 ]; then
    echo "Error: Failed to stop instance. Verify the ID and your permissions."
    exit 1
fi

echo "-----------------------------------------------"
echo "Step 3: Waiting for instance to stop..."
# This pauses the script until the state is 'stopped'
aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID"

echo "-----------------------------------------------"
echo "Success: Instance $INSTANCE_ID has been stopped."
echo "Script execution complete."
