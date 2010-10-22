from boto import connect_s3
from ConfigParser import SafeConfigParser

def get_s3_connection():
    # read the AWS S3 Credentials in from the ini file
    config = SafeConfigParser()
    config.read('server.ini')
    # create an S3 Boto connection
    return connect_s3(config.get('s3', 'access'), config.get('s3', 'secret'))

def get_post_args(bucket, key):
        return get_s3_connection().build_post_form_args(
            bucket_name=bucket,
            key=key,
            expires_in=6000,
            #success_action_redirect='http://{0}:{1}/upload_complete'.format(
            #    self.server.server_name, self.server.server_port),
            fields=[{'name': 'success_action_status',
                     'value': 201}],
            conditions=["['starts-with', '$Filename', '']",
                        "['starts-with', '$folder', '']",
                        "{'success_action_status' : '201'}",]
            )


