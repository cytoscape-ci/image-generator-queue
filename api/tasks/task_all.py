import luigi
import requests
import json
import logging
import binascii
import glob
import os

# Image generator service URL
BASE = 'http://192.168.99.100:5000/'

ID_MAPPING = 'http://52.11.197.18:3000/'

NDEX_URL = 'http://dev2.ndexbio.org/rest/'
NDEX_AUTH = '/user/authenticate'
IMAGE_URL = "http://52.32.158.148/image/"

ID_LIST_FILE = 'id_list.json'


# This is an independent workflow running as a separate process in Luigi.


class RunTask(luigi.Task):

    def output(self):
        return luigi.LocalTarget('report.txt')

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

        logging.warn('Start2 ***************')
        logging.warn(ids)

        for ndex_id in ids:
            yield CacheImage(ndex_id, uid, pw)

        # Consolidate results
        logging.warn('Writing report ***************')
        report_files = glob.glob('/app/report*.txt')

        image_url_list = []
        with self.output().open('w') as f:
            for fl in report_files:
                with open(fl) as report:
                    rep = report.read()
                    image_url_list.append(rep)
                    os.remove(fl)

            json.dump(image_url_list, f)

        logging.warn('------------ Finished2 -----------------')


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


class ConvertID(luigi.Task):

    network_id = luigi.Parameter()
    id = luigi.Parameter()
    pw = luigi.Parameter()

    def requires(self):
        return {
            'cx': GetNetworkFile(self.network_id, self.id, self.pw)
        }

    def output(self):
        return luigi.LocalTarget(str(self.network_id) + '.mapped.json')

    def run(self):

        with self.input()['cx'].open('r') as cxf:
            cx = json.load(cxf)

        query_ids = []

        for entry in cx:
            if 'nodes' in entry:
                for node in entry['nodes']:
                    if 'n' in node:
                        query_ids.append(node['n'])

        query = {
            'ids': query_ids,
            'idTypes': ["GeneID", "Symbol", "UniProtKB-ID", "tax_id", "type_of_gene"]
        }
        res = requests.post(ID_MAPPING+'map', json=query)

        if res.status_code == 200:
            self.__map_ids(res.json(), cx)

        with self.output().open('w') as f:
            json.dump(cx, f)

    def __map_ids(self, mappings, cx):
        id_mapping = {}

        for entry in mappings['matched']:
            id_mapping[entry['in']] = entry['matches']

        node_attributes = []

        for entry in cx:
            if 'nodes' in entry:
                for node in entry['nodes']:
                    node_id = node['@id']
                    if 'n' in node:
                        original_id = node['n']

                        if original_id in id_mapping and 'Symbol' in id_mapping[original_id]:
                            original_entry = id_mapping[node['n']]
                            node['n'] = original_entry['Symbol']
                            # Create Tax_id attribute
                            if 'tax_id' in id_mapping[original_id]:
                                tax_id = {
                                    'n': 'tax_id',
                                    'po': node_id,
                                    'v': original_entry['tax_id']
                                }
                                node_attributes.append(tax_id)
                                logging.warn('****** GOT TAX: ' + str(tax_id))
                            if 'type_of_gene' in id_mapping[original_id]:
                                type_of_gene = {
                                    'n': 'type_of_gene',
                                    'po': node_id,
                                    'v': original_entry['type_of_gene']
                                }
                                node_attributes.append(type_of_gene)

        cx.append({'nodeAttributes': node_attributes})



class GenerateImage(luigi.Task):

    network_id = luigi.Parameter()
    id = luigi.Parameter()
    pw = luigi.Parameter()

    def requires(self):
        return {
            'cx': ConvertID(self.network_id, self.id, self.pw)
        }

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
        os.remove(str(self.network_id) + '.mapped.json')
        logging.warn('%%%%%%%%%%% Done: ' + str(self.network_id))


class CacheImage(luigi.Task):

    network_id = luigi.Parameter()
    id = luigi.Parameter()
    pw = luigi.Parameter()

    def requires(self):
        return {'gen': GenerateImage(self.network_id, self.id, self.pw)}

    def output(self):
        return luigi.LocalTarget('report.' + str(self.network_id) + '.txt')

    def run(self):

        image_cache_url = IMAGE_URL + 'svg/' + str(self.network_id)

        with self.input()['gen'].open('r') as f:
            img_data = f.read()

        img = binascii.a2b_qp(img_data)
        res = requests.post(image_cache_url, data=img)

        status_code = res.status_code
        if status_code is not 200:
            logging.warn('Failed to POST image file')

        # Remove input file
        with self.output().open('w') as result:
            result.write(IMAGE_URL + str(self.network_id))


if __name__ == '__main__':
    luigi.run(['RunTask', '--workers', '5'])
