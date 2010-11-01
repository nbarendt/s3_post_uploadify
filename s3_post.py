from boto import connect_s3
from ConfigParser import SafeConfigParser
import os


class S3PostArgGenerator(object):

    def __init__(self):
        self.s3_conn = self._create_s3_connection()

    def _get_s3_credentials(self): 
        CONFIG_FILE='server.ini'
        # read the AWS S3 Credentials in from the ini file
        config = SafeConfigParser()
        err_msg = 'Required file %s not found!' % CONFIG_FILE
        assert os.path.exists(CONFIG_FILE), err_msg
        config.read(CONFIG_FILE)
        return config.get('s3', 'access'), config.get('s3', 'secret')

    def _create_s3_connection(self):
        access_key, secret_key = self._get_s3_credentials()
        return connect_s3(access_key, secret_key)

    def get_post_args(self, bucket, key):
        return self.s3_conn.build_post_form_args(
            bucket_name=bucket,
            key=key,
            expires_in=6000,
            fields=[{'name': 'success_action_status',
                     'value': 201}],
            conditions=["['starts-with', '$Filename', '']",
                        "['starts-with', '$folder', '']",
                        "{'success_action_status' : '201'}",]
            )


