#!/bin/bash

# --- Authentication Check ---
if ! aws sts get-caller-identity &> /dev/null; then
    echo "ERROR: AWS authentication failed. Please run 'aws configure'."
    exit 1
fi

echo "----------------------------------------------------------------------------------------"
printf "%-20s %-15s %-15s %-30s\n" "INSTANCE_ID" "STATE" "IPV4_ADDRESS" "IPV6_ADDRESS"
echo "----------------------------------------------------------------------------------------"

# Querying in exact order: ID (1), State (2), IPv4 (3), IPv6 (4)
aws ec2 describe-instances \
    --query "Reservations[*].Instances[*].[InstanceId, State.Name, PublicIpAddress, NetworkInterfaces[0].Ipv6Addresses[0].Ipv6Address]" \
    --output text | while read -r id state ipv4 ipv6
do
    # Handle cases where values are null (output as 'None' or empty)
    [ "$ipv4" == "None" ] && ipv4="N/A"
    [ "$ipv6" == "None" ] && ipv6="N/A"

    printf "%-20s %-15s %-15s %-30s\n" "$id" "$state" "$ipv4" "$ipv6"
done
echo "----------------------------------------------------------------------------------------"
