#! /usr/bin/env python
from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
from boto import connect_s3
from uuid import uuid4
from ConfigParser import SafeConfigParser

# read the AWS S3 Credentials in from the ini file
config = SafeConfigParser()
config.read('server.ini')
# create an S3 Boto connection
conn = connect_s3(config.get('s3', 'access'), config.get('s3', 'secret'))

GET_TEMPLATE = u"""
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
</head>
<body>

    <p>
        Key: {key}
    </p>
    <form action="{action}" method="post" enctype="multipart/form-data">
        {hidden_fields}
        <br/>
        <!-- file must be last field -->
        File: <input type="file" name="file"/> <br/>
        <input type="submit" name="submit" value="Submit"/> 
    </form>
</body>
</html>
"""

BUCKET_NAME = 'edacloud_media_test'

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        key = uuid4().hex
        s3_post_args = conn.build_post_form_args(bucket_name=BUCKET_NAME,
            key=key,
            expires_in=6000)
        hidden_fields = ''
        for field in s3_post_args['fields']:
            hidden_fields += ' '.join(['<input',
                                    'type="hidden"',
                                    'name="{0}" value="{1}"'.format(
                                        field['name'], field['value']),
                                    '/>\n'])
    
        d = {
            'hostname': self.server.server_name,
            'port' : self.server.server_port,
            'hidden_fields' : hidden_fields,
            'action' : s3_post_args['action'],
            'key' : key,
        }
            
        self.wfile.write(GET_TEMPLATE.format(**d))
        return

def main():
    server = HTTPServer(('', 8080), MyHandler)
    print 'HTTP Server starting on {0}:{1}'.format(server.server_name,
        server.server_port)
    server.serve_forever()

if __name__ == '__main__':
    main()



