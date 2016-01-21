from flask_restful import Resource
from flask import request
import subprocess
import glob
import os
import logging
import json


class Runner(Resource):

    def post(self):

        # Cleanup (Old SVG files in the system
        img_files = glob.glob('/app/*.svg')
        report_files = glob.glob('/app/report*.txt')

        to_be_removed = img_files + report_files

        for fl in to_be_removed:
            logging.info('* Removing old file: ' + str(fl.title()))
            os.remove(fl)

        # Save file for Luigi task
        with open('id_list.json', 'w') as f:
            f.write(request.stream.read().decode('utf-8'))

        subprocess.call(['/app/api/run_luigi.sh'])

        os.remove('id_list.json')

        try:
            with open('report.txt') as report:
                data = json.load(report)
        except FileNotFoundError:
            return {"message": "Failed to run the workflow."}, 500

        logging.warn("Final result================")
        logging.warn(data)

        result_msg = {"image_urls": data}

        try:
            os.remove('report.txt')
        except FileNotFoundError:
            pass

        return result_msg
