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
        self.image_id = self.cloud_config.get(self.name, "image_id")
        self.instance_type = self.cloud_config.get(self.name, "instance_type")
        aid = self.cloud_config.get(self.name, "access_id")
        self.access_var = aid.strip('$')
        sk = self.cloud_config.get(self.name, "secret_key")
        self.secret_var = sk.strip('$')
        self.access_id = os.environ[self.access_var]
        self.secret_key = os.environ[self.secret_var]
        if self.cloud_type is "nimbus":
            self.cloud_port = int(self.cloud_config.get(self.name, "cloud_port"))
        elif self.cloud_type is "openstack":
            self.project_id = self.cloud_config.get(self.name, "project_id")
        self.conn = None

    def connect(self):
        """Connects to the cloud using boto interface"""
        
        print "Connecting to cloud of type: " + str(self.cloud_type)
        if self.cloud_type is "nimbus":
            self.region = RegionInfo(name=self.cloud_type, endpoint=self.cloud_uri)
            self.conn = EC2Connection(
                self.access_id, self.secret_key,
                port=self.cloud_port, region=self.region, validate_certs=False)
            self.conn.host = self.cloud_uri
        elif self.cloud_type is "openstack":
            self.creds = get_nova_creds()
            self.conn = nvclient.Client(**self.creds)
        LOG.debug("Connected to cloud: %s" % (self.name))

    def register_key(self):
        """Registers the public key that will be used in the launched
        instance

        """

        with open(self.config.globals.key_path, 'r') as key_file_object:
            key_content = key_file_object.read().strip()
        import_result = self.conn.import_key_pair(self.config.globals.key_name,
                                                  key_content)
        LOG.debug("Registered key \"%s\"" % (self.config.globals.key_name))
        return import_result

    def boot_image(self):
        """Registers the public key and launches an instance of specified
        image

        """

        # Check if a key with specified name is already registered. If
        # not, register the key
        registered = False
        print "Checking if public key is registered"
        for key in self.conn.get_all_key_pairs():
            print "Key is: " + str(key.name)
            if key.name == self.config.globals.key_name:
                print str(key.name) + " is registered"
                registered = True
                break
        if not registered:
            print "Registering"
            self.register_key()
        else:
            LOG.debug("Key \"%s\" is already registered" %
                      (self.config.globals.key_name))

        print "Successfully registered keys"
        image_object = self.conn.get_image(self.image_id)
        boot_result = image_object.run(key_name=self.config.globals.key_name,
                                       instance_type=self.instance_type)
        LOG.debug("Attempted to boot an instance. Result: %s" % (boot_result))
        return boot_result

class NovaCloud(object):

    """
    Should provide functionality to connect to OpenStack clouds using the 
    Nova API.
    """

    def __init__(self):
        self.creds = get_nova_creds()
        self.nova = nvclient.Client(**self.creds)

        print "Checking for keypair and importing if not found"
        if not self.nova.keypairs.findall(name="mykey"):
            with open(os.path.expanduser('~/.ssh/id_rsa.pub')) as fpubkey:
                self.nova.keypairs.create(name="mykey", public_key=fpubkey.read())


        self.image = self.nova.images.find(name="futuregrid/ubuntu-12.04")
        self.flavor = self.nova.flavors.find(name="m1.tiny")

    def boot_image(self, name):
        print "Creating instance of " + str(self.image) + " of flavor " + str(self.flavor)
        instance = self.nova.servers.create(name=name, image=self.image, 
                                            flavor=self.flavor, key_name="mykey")

        # Poll at 5 second intervals, until the status is no longer 'BUILD'
        status = instance.status
        while status == 'BUILD':
            time.sleep(5)
            # Retrieve the instance again so the status field updates
            instance = self.nova.servers.get(instance.id)
            status = instance.status
            
        print "status: %s" % status

    def destroy(self, name):
        print "Deleting instance " + name
        try:
            server = self.nova.servers.find(name=name)
            server.delete()
        except exception.NotFound:
            print "Instance of name " + name + " not found"



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
