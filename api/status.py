from flask_restful import Resource


class Status(Resource):

    def get(self):

        status = {
            'serviceName': 'Image generator queue',
            'description': 'Generate image from list of NDEx IDs',
            'apiVersion': 'v1',
            'buildVersion': '0.1.2'
        }

        return status
