#!/bin/bash

# --- CONFIGURATION ---
# Replace with the actual Instance ID
INSTANCE_ID="i-020b6ffa22e32cd83"

echo "-----------------------------------------------"
echo "Step 1: Verifying AWS Authentication..."
# Checks if the CLI is currently configured with valid credentials
aws sts get-caller-identity > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "Successfully authenticated."
else
    echo "Error: Not authenticated. Run 'aws configure' to set up credentials."
    exit 1
fi

echo "-----------------------------------------------"
echo "Step 2: Starting EC2 Instance ($INSTANCE_ID)..."
aws ec2 start-instances --instance-ids "$INSTANCE_ID" --output json

if [ $? -ne 0 ]; then
    echo "Error: Failed to send start command. Verify Instance ID and Permissions."
    exit 1
fi

echo "-----------------------------------------------"
echo "Step 3: Waiting for instance to reach 'running' state..."
echo "This process may take a short period..."

# This command pauses the script until the instance state is 'running'
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"

echo "-----------------------------------------------"
echo "Success: Instance $INSTANCE_ID is now running."
echo "Script execution complete."
