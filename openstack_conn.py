import os
from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo

access_id = os.environ['AWS_ACCESS_KEY']
secret_key = os.environ['AWS_SECRET_KEY']
cloud_uri = '198.202.120.83'
cloud_port = '8773'
image_id = 'futuregrid/ubuntu-12.04'
cloud_type = 'grizzly'

region = RegionInfo(name=cloud_type, endpoint=cloud_uri)
conn = EC2Connection(access_id, secret_key, is_secure=False, 
                     path='/services/Cloud/', port = cloud_port, 
                     region=region, validate_certs=False)
