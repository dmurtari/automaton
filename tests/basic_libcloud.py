import os
from libcloud.compute.types import Provider
from libcloud.compute.providers import get_driver
import libcloud.security

# https://libcloud.readthedocs.org/en/latest/other/ssl-certificate-validation.html#acquiring-ca-certificates
libcloud.security.VERIFY_SSL_CERT = False

access_id = os.environ['AWS_ACCESS_KEY']
secret_key = os.environ['AWS_SECRET_KEY']
cloud_uri = 'http://198.202.120.83:8773/services/Cloud'
cloud_port = 8773
path = '/services/Cloud'

driver = get_driver(Provider.OPENSTACK)
fg_compute = driver(access_id, secret_key,
                    ex_force_auth_url=cloud_uri,
                    ex_force_auth_version='2.0_password')
