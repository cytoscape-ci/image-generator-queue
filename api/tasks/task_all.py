import luigi
import requests
import json
import os
import logging


BASE = 'http://52.35.133.2:5000/'
NDEX_URL = 'http://dev2.ndexbio.org/rest/'
NDEX_AUTH = '/user/authenticate'

ID_LIST_FILE = 'id_list.json'


# This is an independent workflow running as a separate process in Luigi.


class RunTask(luigi.Task):

    def run(self):
        with open(ID_LIST_FILE, 'r') as f:
            data = json.load(f)

        # List of NDEx IDs
        ids = data['ids']

        # Credential is optional

        uid = ""
        pw = ""
        if 'credential' in data:
            uid = data['credential']['id']
            pw = data['credential']['password']

        logging.warn('************** RUN ***************')

        for ndex_id in ids:
            yield GenerateImage(ndex_id, uid, pw)


class GetNetworkFile(luigi.Task):

    network_id = luigi.Parameter()
    id = luigi.Parameter()
    pw = luigi.Parameter()

    def output(self):
        return luigi.LocalTarget(str(self.network_id) + '.json')

    def run(self):
        with self.output().open('w') as f:

            # Check optional parameter
            s = requests.session()

            if self.id is not "" and self.pw is not "":
                s.auth = (self.id, self.pw)
                res = s.get(NDEX_URL + NDEX_AUTH)

                if res.status_code != 200:
                    raise ValueError('Invalid credential given.')

            network_url = NDEX_URL + 'network/' + self.network_id + '/asCX'

            response = s.get(network_url, stream=True)

            # Error check: 401 may be given
            if response.status_code != 200:
                logging.warn('!!!!!!!!!!!!!!!!!!!!!!!Error getting CX network: CODE ' + str(response.status_code))
                raise RuntimeError("Could not fetch CX network file.")

            for block in response.iter_content(1024):
                f.write(block.decode('utf-8'))


class GenerateImage(luigi.Task):

    network_id = luigi.Parameter()
    id = luigi.Parameter()
    pw = luigi.Parameter()

    def requires(self):
        return {'cx': GetNetworkFile(self.network_id, self.id, self.pw)}

    def output(self):
        return luigi.LocalTarget("graph_image_" + self.network_id + ".svg")

    def run(self):
        with self.output().open('w') as f:
            svg_image_url = BASE + 'image/svg'
            cx_file = self.input()['cx'].open('r')
            data = json.loads(cx_file.read())
            res = requests.post(svg_image_url, json=data)
            cx_file.close()

            f.write(res.content.decode('utf-8'))

        # Remove input file
        os.remove(str(self.network_id) + '.json')
        logging.warn('%%%%%%%%%%% Done: ' + str(self.network_id))
        with open('report.txt', 'a') as result:
            result.write('http://example.com/' + str(self.network_id) + ".svg\n")


if __name__ == '__main__':
    luigi.run(['RunTask', '--workers', '5'])
