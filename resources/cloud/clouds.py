import logging
import os
import time

from boto.ec2.connection import EC2Connection
from boto.ec2.regioninfo import RegionInfo
import novaclient.exceptions as exception
import novaclient.v1_1.client as nvclient
from credentials import get_nova_creds

LOG = logging.getLogger(__name__)


class Cloud(object):
    """Cloud class provides functionality for connecting to a specified
    cloud and launching an instance there

    cloud_name should match one of the section names in the file that
    specifies cloud information

    """

    def __init__(self, cloud_name, config):
        self.config = config
        self.name = cloud_name
        self.cloud_config = self.config.clouds.config
        self.cloud_uri = self.cloud_config.get(self.name, "cloud_uri")
        self.cloud_type = self.cloud_config.get(self.name, "cloud_type")
        aid = self.cloud_config.get(self.name, "access_id")
        self.access_var = aid.strip('$')
        sk = self.cloud_config.get(self.name, "secret_key")
        self.secret_var = sk.strip('$')
        self.access_id = os.environ[self.access_var]
        self.secret_key = os.environ[self.secret_var]
        if self.cloud_type == "nimbus":
            self.cloud_port = int(self.cloud_config.get(self.name, "cloud_port"))
            self.image_id = self.cloud_config.get(self.name, "image_id")
            self.instance_type = self.cloud_config.get(self.name, "instance_type")
        elif self.cloud_type == "openstack":
            self.project_id = self.cloud_config.get(self.name, "project_id")
        self.conn = None

    def connect(self):
        """Connects to the cloud using boto interface"""
        
        print "Connecting to cloud of type: " + str(self.cloud_type)
        if self.cloud_type == "nimbus":
            self.region = RegionInfo(name=self.cloud_type, endpoint=self.cloud_uri)
            self.conn = EC2Connection(
                self.access_id, self.secret_key,
                port=self.cloud_port, region=self.region, validate_certs=False)
            self.conn.host = self.cloud_uri
        elif self.cloud_type == "openstack":
            self.creds = get_nova_creds()
            self.conn = nvclient.Client(**self.creds)
            self.image_id = self.conn.images.find(name=self.cloud_config.get(self.name, "image_id"))
            self.instance_type = self.conn.flavors.find(name=self.cloud_config.get(self.name, "instance_type"))
        LOG.debug("Connected to cloud: %s" % (self.name))

    def register_key(self):
        """Registers the public key that will be used in the launched
        instance

        """

        with open(self.config.globals.key_path, 'r') as key_file_object:
            key_content = key_file_object.read().strip()
        if self.cloud_type == "nimbus":
            import_result = self.conn.import_key_pair(self.config.globals.key_name,
                                                  key_content)
        elif self.cloud_type == "openstack":
            print "registering openstack key"
            import_result = self.conn.keypairs.create(name=self.config.globals.key_name, 
                                        public_key=key_content)
        LOG.debug("Registered key \"%s\"" % (self.config.globals.key_name))
        return import_result

    def boot_image(self):
        """Registers the public key and launches an instance of specified
        image

        """

        # Check if a key with specified name is already registered. If
        # not, register the key
        registered = True
        print "Checking if public key is registered"
        if self.cloud_type == "nimbus":
            print "checking nimbus key"
            for key in self.conn.get_all_key_pairs():
                print "Key is: " + str(key.name)
                if not key.name == self.config.globals.key_name:
                    print str(key.name) + " is not registered"
                    registered = False
                    break
        elif self.cloud_type == "openstack":
            print "checking openstack key"
            if not self.conn.keypairs.findall(name=self.config.globals.key_name):
                print "openstack key is not registered"
                registered = False
        if not registered:
            print "Registering"
            self.register_key()
        else:
            LOG.debug("Key \"%s\" is already registered" %
                      (self.config.globals.key_name))

        print "Successfully registered keys"
        print "Creating instance of " + str(self.image_id) + " of flavor " + str(self.instance_type) + \
              " using key " + str(self.config.globals.key_name)
        
        
        if self.cloud_type == "nimbus":
            image_object = self.conn.get_image(self.image_id)
            boot_result = image_object.run(key_name=self.config.globals.key_name,
                                           instance_type=self.instance_type)
        elif self.cloud_type == "openstack":
            instance = self.conn.servers.create(name="test", 
                                                image=self.image_id, 
                                                flavor=self.instance_type, 
                                                key_name=self.config.globals.key_name) 
            boot_result = instance.status                                       
        LOG.debug("Attempted to boot an instance. Result: %s" % (boot_result))
        return boot_result

class Clouds(object):
    """Clusters class represents a collection of clouds specified in the
    clouds file

    """

    def __init__(self, config):
        self.config = config
        self.list = list()
        for cloud_name in self.config.clouds.list:
            self.list.append(Cloud(cloud_name, self.config))

    def lookup_by_name(self, name):
        """Finds a cloud in the collection with a given name; if does not
        exist, returns None

        """

        for cloud in self.list:
            if cloud.name == name:
                return cloud
        return None
