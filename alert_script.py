import boto3
import json
import logging
from datetime import datetime

#defining clients
ec2_client = boto3.client('ec2')
sns_client = boto3.client('sns')
s3_client = boto3.client('s3')

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configuration variables
SNS_TOPIC_ARN = 'arn:aws:sns:ap-south-1:711387098945:Alerting'
S3_BUCKET_NAME = 'logging-bucket-oct24'
S3_LOG_FILE_PREFIX = 'ec2-health-check-logs'

def check_ec2_health(region):
    # Get EC2 instance statuses
        ec2_client = boto3.client('ec2', region_name=region)
        statuses = ec2_client.describe_instance_status(IncludeAllInstances=True)['InstanceStatuses']
    
        unhealthy_instances = []
        all_instances = []

        for status in statuses:
            instance_id = status['InstanceId']
            instance_state = status['InstanceState']['Name']
            system_status = status['SystemStatus']['Status']
            instance_status = status['InstanceStatus']['Status']
        
        instance_info = {
            'InstanceId': instance_id,
            'State': instance_state,
            'SystemStatus': system_status,
            'InstanceStatus': instance_status
        }
        all_instances.append(instance_info)

        if system_status != 'ok' or instance_status != 'ok':
            unhealthy_instances.append(instance_info)

        return all_instances, unhealthy_instances
  
def send_sns_alert(unhealthy_instances, region):
    if unhealthy_instances:
        for instance in unhealthy_instances:
            message = (f"EC2 Health Check Alert:\n\n"
                       f"Instance ID: {instance['InstanceId']}\n"
                       f"State: {instance['State']}\n"
                       f"System Status: {instance['SystemStatus']}\n"
                       f"Instance Status: {instance['InstanceStatus']}")
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=message,
                Subject="EC2 Health Check Alert"
            )
        logger.info(f"Sent alert for {len(unhealthy_instances)} unhealthy instances via SNS")
    else:
        logger.info("All instances are healthy")
        
def store_logs_in_s3(log_data):
    timestamp = datetime.now().strftime('%Y-%m-%dT%H-%M-%S')
    file_name = f"{S3_LOG_FILE_PREFIX}/{timestamp}.log"

    # Convert log data to string and store it
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=file_name,
        Body=json.dumps(log_data, indent=2)
    )
    logger.info(f"Logs stored in S3 at {file_name}")
    
def lambda_handler(event, context):
    region = event.get('region', 'ap-south-1')
    all_instances, unhealthy_instances = check_ec2_health(region)

    # Log the health status of all instances and send alerts for unhealthy ones
    log_data = {
        'timestamp': datetime.now().isoformat(),
        'region': region,
        'all_instances': all_instances
    }

    send_sns_alert(unhealthy_instances, region)
    store_logs_in_s3(log_data)

    return {
        'statusCode': 200,
        'body': json.dumps(log_data)
    }
