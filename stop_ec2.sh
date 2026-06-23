#!/bin/bash

# --- CONFIGURATION ---
INSTANCE_ID="i-020b6ffa22e32cd83"

echo "-----------------------------------------------"
echo "Step 1: Verifying AWS Authentication..."
aws sts get-caller-identity > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "Successfully authenticated."
else
    echo "Error: Not authenticated. Run 'aws configure'."
    exit 1
fi

echo "-----------------------------------------------"
echo "Step 2: Sending Stop Command to $INSTANCE_ID..."
# Displaying stop status in a table format
aws ec2 stop-instances --instance-ids "$INSTANCE_ID" --query "StoppingInstances[*].{ID:InstanceId, CurrentState:PreviousState.Name, TargetState:CurrentState.Name}" --output table

if [ $? -ne 0 ]; then
    echo "Error: Failed to send stop command."
    exit 1
fi

echo "-----------------------------------------------"
echo "Step 3: Waiting for instance to stop..."
aws ec2 wait instance-stopped --instance-ids "$INSTANCE_ID"

echo "-----------------------------------------------"
echo "Final Status Report:"
printf "%-20s %-15s %-15s %-30s\n" "INSTANCE_ID" "STATE" "IPV4_ADDRESS" "IPV6_ADDRESS"
echo "----------------------------------------------------------------------------------------"

# Integrated status check
aws ec2 describe-instances \
    --instance-ids "$INSTANCE_ID" \
    --query "Reservations[*].Instances[*].[InstanceId, State.Name, PublicIpAddress, NetworkInterfaces[0].Ipv6Addresses[0].Ipv6Address]" \
    --output text | while read -r id state ipv4 ipv6
do
    [ "$ipv4" == "None" ] && ipv4="N/A"
    [ "$ipv6" == "None" ] && ipv6="N/A"
    printf "%-20s %-15s %-15s %-30s\n" "$id" "$state" "$ipv4" "$ipv6"
done

echo "----------------------------------------------------------------------------------------"
echo "Success: Instance $INSTANCE_ID is now stopped."
echo "Script execution complete."
