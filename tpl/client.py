import tpl.tools
import trompace.connection
import trompace
import trompace.queries.templates
import trompace.mutations.controlaction
import asyncio
import argparse
import configparser
import types

class TPLclient():
    def __init__(self, client_config, ce_config):
        self.config = client_config
        trompace.config.config.load(client_config)
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(client_config)
        self.authenticate = self.config_parser.getboolean('auth', 'required')
        self.inputs_n = int(self.config_parser['application']['inputs_n'])
        self.params_n = int(self.config_parser['application']['params_n'])
        self.ep_id = self.config_parser['application']['ep_id']
        self.ca_id = self.config_parser['application']['ca_id']

        self.inputs = {}
        self.params = {}

        for i in range(self.inputs_n):
            label = 'Input{}'.format(i + 1)
            property = self.config_parser['Input{}'.format(i + 1)]
            check_pro = ['name', 'title', 'description', 'rangeincludes']
            if not all(x in property.keys() for x in check_pro):
                missing_fields = [x for x in check_pro if x not in property.keys()]
                raise trompace.exceptions.ConfigRequirementException(missing_fields)
            input_property = types.SimpleNamespace()
            input_property.name = property['name']
            input_property.title = property['title']
            input_property.description = property['description']
            input_property.rangeIncludes = trompace.StringConstant(property['rangeIncludes'])
            if self.config_parser.has_option('Input{}'.format(i + 1), 'id'):
                input_property.id = self.config_parser['Input{}'.format(i + 1)]['id']
            self.inputs[label] = input_property

        for i in range(self.params_n+1):
            label = 'Param{}'.format(i + 1)
            if i < self.params_n:
                label = 'Param{}'.format(i + 1)
            else:
                label = 'Storage'
            property = self.config_parser[label]
            check_pro = ['name', 'description', 'defaultValue', 'valuemaxlength', 'valueminlength', 'multiplevalues',
                         'valuename', 'valuepattern', 'valuerequired']
            if not all(x in property.keys() for x in check_pro):
                missing_fields = [x for x in check_pro if x not in property.keys()]
                raise trompace.exceptions.ConfigRequirementException(missing_fields)
            param_property = types.SimpleNamespace()
            param_property.name = property['name']
            param_property.description = property['description']
            param_property.defaultValue = property['defaultValue']
            param_property.valueMaxLength = int(property['valuemaxlength'])
            param_property.valueMinLength = int(property['valueminlength'])
            param_property.multipleValues = property.getboolean('multiplevalues')
            param_property.valueName = property['valuename']
            param_property.valuePattern = property['valuepattern']
            param_property.valueRequired = property.getboolean('valuerequired')
            if self.config_parser.has_option(label, 'id'):
                param_property.id = self.config_parser[label]['id']

            self.params[label] = param_property

        self.connection_parser = configparser.ConfigParser()
        self.connection_parser.read(ce_config)
        self.encrypt_fn = self.connection_parser.get('tplKey', 'keyFile')
        file = open(self.encrypt_fn, 'rb')
        self.key = file.read()
        file.close()

    def send_request(self, input_documents, param_values, storage, execute=True):

        # it sends a request for the corresponding entry point and input to the algorithms a list of values
        # (input_values) that are the actual input of the algorithm. The number of items of input_values should be the
        # same with self.inputs_n
        if len(input_documents) != self.inputs_n:
            print("Wrong number of inputs")
            return

        inputs_list_raw = []
        for i in range(self.inputs_n):
            label = 'Input{}'.format(i + 1)
            param_input = {
                "nodeIdentifier":input_documents[i],
                "potentialActionPropertyIdentifier":self.inputs[label].id,
                "nodeType": trompace.StringConstant(self.inputs[label].rangeIncludes)
            }

            inputs_list_raw.append(param_input)
        params_list_raw = []
        for i in range(self.params_n):
            label = 'Param{}'.format(i + 1)
            param_input = {
                "value": param_values[i],
                "potentialActionPropertyValueSpecificationIdentifier": self.params[label].id,
                "valuePattern": trompace.StringConstant(self.params[label].valuePattern)
            }
            params_list_raw.append(param_input)

        fp = open(storage, 'r')
        storage_str = fp.read()
        fp.close()
        storage_str_encrypted = tpl.tools.ecrypt_string(storage_str, self.key)

        label = 'Storage'
        param_input = {
            "value": storage_str_encrypted,
            "potentialActionPropertyValueSpecificationIdentifier": self.params[label].id,
            "valuePattern": trompace.StringConstant(self.params[label].valuePattern)
        }
        params_list_raw.append(param_input)


        qry = trompace.mutations.controlaction.mutation_request_controlaction(self.ca_id,self.ep_id, inputs_list_raw,
                                                                              params_list_raw)
        if execute:
            response = trompace.connection.submit_query(qry, auth_required=self.authenticate)
            print(response)
            return response
        else:
            return qry


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='')

    parser.add_argument('--client_ini',  type=str)
    parser.add_argument('--ce_ini',  type=str)
    parser.add_argument('--inputs', nargs='+')
    parser.add_argument('--params', nargs='+')
    parser.add_argument('--storage_info', type=str)
   # parser.add_argument('--tpl_key', nargs='+')

    args = parser.parse_args()
    tpl_client = TPLclient(args.client_ini, args.ce_ini)
    inputs = args.inputs
    params = args.params
    storage = args.storage_info

    if inputs is None:
        inputs = []
    if params is None:
        params = []

    tpl_client.send_request(inputs, params, storage, execute=False)

  #  asyncio.run(get_all_control_actions())
