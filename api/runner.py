from flask_restful import Resource
from flask import request
import subprocess
import glob
import os
import logging


class Runner(Resource):

    def post(self):
        # Cleanup (Old SVG files in the system
        for fl in glob.glob('/app/*.svg'):
            logging.info('Removing old files: ' + str(fl.title()))
            os.remove(fl)


        # Save file for Luigi task
        with open('id_list.json', 'w') as f:
            f.write(request.stream.read().decode('utf-8'))

        subprocess.call(['/app/api/run_luigi.sh'])

        os.remove('id_list.json')
        logging.info('ID list file removed')

        try:
            with open('report.txt', 'r') as res:
                results = res.readlines()
        except FileNotFoundError:
            return {"message": "Failed to run the workflow."}, 500



        resultMsg = {"imageLocations": results}

        try:
            os.remove('report.txt')
        except FileNotFoundError:
            pass

        return resultMsg
