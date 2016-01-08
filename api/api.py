from flask import Flask
from flask_restful import Api

from status import Status
from runner import Runner


app = Flask(__name__)
api = Api(app)

# Routing
api.add_resource(Status, '/')
api.add_resource(Runner, '/generator')


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=3001, use_reloader=False)
