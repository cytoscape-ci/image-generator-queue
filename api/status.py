from flask_restful import Resource


class Status(Resource):

    def get(self):

        status = {
            'serviceName': 'Image generator queue',
            'description': 'Generate image from list of NDEx IDs',
            'version': 'v1'
        }

        return status
