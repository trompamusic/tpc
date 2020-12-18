import configparser
import asyncio
import websockets
import types
import json
import argparse
import uuid
import minio
import tpl.tools
import os

import trompace
import trompace.config
import trompace.mutations.person
import trompace.mutations.application
import trompace.mutations.controlaction
import trompace.mutations.entrypoint
import trompace.mutations.property
import trompace.mutations.templates
import trompace.mutations.digitaldocument

import trompace.connection
import trompace.exceptions
import trompace.subscriptions.controlaction
import trompace.queries.controlaction
import tpl.tools
import validators
'''Script of the TROMPA Processing Library class.
'''


class TPLapp():
    def __init__(self, application_config, ce_config):

        '''
        the class constructor reads the application configuration file and the ce configuration file, stores all the
        needed and also initializes the ce-client connection
        '''

        # create a CE connection
        self.ce_config = ce_config
        self.application_config = application_config
        trompace.config.config.load(ce_config)
        self.secure = trompace.config.config.secure

        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(application_config)
        self.connection_parser = configparser.ConfigParser()
        self.connection_parser.read(ce_config)

        self.application_name = self.config_parser['Application']['name']
        self.contributor = self.config_parser['Application']['contributor']
        self.creator = self.config_parser['Application']['creator']
        self.source = self.config_parser['Application']['source']
        self.subject = self.config_parser['Application']['subject']
        self.description = self.config_parser['Application']['description']
        self.language = self.config_parser['Application']['language']
        if self.config_parser.has_option('Application', 'id'):
            self.application_id = self.config_parser['Application']['id']
            self.registered = True
        else:
            self.registered = False

        self.language = self.config_parser['Application']['language']
        self.data_path = self.config_parser['data']['path']

        self.control_action = self.config_parser['ControlAction']['name']
        self.inputs_n = int(self.config_parser['ControlAction']['num_inputs'])
        self.params_n = int(self.config_parser['ControlAction']['num_params'])
        self.outputs_n = int(self.config_parser['ControlAction']['num_outputs'])

        if self.config_parser.has_option('ControlAction', 'id'):
            self.controlaction_id = self.config_parser['ControlAction']['id']

        self.content_type = self.config_parser['EntryPoint']['content_type']
        self.encoding_type = self.config_parser['EntryPoint']['encoding_type']
        self.action_platform = self.config_parser['EntryPoint']['action_platform']
        if self.config_parser.has_option('EntryPoint', 'id'):
            self.entrypoint_id = self.config_parser['EntryPoint']['id']
        self.requires_docker = self.config_parser.getboolean('EntryPoint', 'requires_docker')
        self.command_line = self.config_parser['EntryPoint']['command_line']

        # load connection/secutiry information
        self.encrypt_fn = self.connection_parser.get('tplKey', 'keyFile')
        self.s3_secure = self.connection_parser.getboolean('s3', 'secure')
        self.s3_key = self.connection_parser.get('s3', 'access_key')
        self.s3_secret = self.connection_parser.get('s3', 'secret_key')
        self.s3_server = self.connection_parser.get('s3', 'server')
        self.s3_public_server = self.connection_parser.get('s3', 'public_server')
        self.authenticate = self.connection_parser.getboolean('auth','required')
        #minio client for uploading results
        self.minioclient = minio.Minio(
            self.s3_server,
            access_key=self.s3_key,
            secret_key=self.s3_secret,
            secure=self.s3_secure,
        )
        #
        if not self.minioclient.bucket_exists("tpl"):
            self.minioclient.make_bucket("tpl")

        self.inputs = {}
        self.params = {}
        self.outputs = {}
        self.command_dictionary = {}

        ''' Read the inputs '''
        for i in range(self.inputs_n):
            label = 'Input{}'.format(i + 1)
            property = self.config_parser[label]
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
            input_property.argument = input_property.title
            input_property.encrypted = property.getboolean('encrypted')
            self.inputs[label] = input_property
            self.inputs[input_property.title] = label
            self.command_dictionary[label] = ""

        ''' Read the params '''
        for i in range(self.params_n):
            label = 'Param{}'.format(i + 1)
            property = self.config_parser[label]
            check_pro = ['name', 'description', 'defaultValue', 'valuemaxlength', 'valueminlength', 'multiplevalues',
                         'valueName', 'valuepattern', 'valuerequired']
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
            if self.config_parser.has_option('Param{}'.format(i + 1), 'id'):
                param_property.id = self.config_parser['Param{}'.format(i + 1)]['id']
            param_property.encrypted = property.getboolean('encrypted')
            param_property.argument = param_property.valueName
            self.params[label] = param_property
            self.command_dictionary[label] = ""

        ''' Read the outputs '''
        for i in range(self.outputs_n):
            label = 'Output{}'.format(i + 1)
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
            param_property.argument = param_property.valueName
            param_property.encrypted = property.getboolean('encrypted')
            param_property.mimeType = property.get('mimeType')
            self.outputs[label] = param_property

        ''' Read the encryption key '''
        file = open(self.encrypt_fn, 'rb')
        self.key = file.read()
        file.close()
        self.constants = dict()
        self.constants['*TPL_DATA'] = self.s3_public_server

    def register(self):

        ''' Stores or information in the CE; i.e. it creates all the nodes and the interlining needed '''

        qry = trompace.mutations.application.mutation_create_application(
            application_name=self.application_name,
            contributor=self.contributor,
            creator=self.creator,
            source=self.source,
            subject=self.subject,
            description=self.description,
            language=self.language)

        response = trompace.connection.submit_query(qry, auth_required=self.authenticate)

        self.application_id = response['data']['CreateSoftwareApplication']['identifier']
        self.config_parser['Application']['id'] = self.application_id

        qry = trompace.mutations.controlaction.mutation_create_controlaction(name=self.control_action,
                                                                             description=self.description)
        response = trompace.connection.submit_query(qry, auth_required=self.authenticate)
        self.controlaction_id = response['data']['CreateControlAction']['identifier']
        self.config_parser['ControlAction']['id'] = self.controlaction_id

        qry = trompace.mutations.entrypoint.mutation_create_entry_point(
            name=self.application_name,
            contributor=self.contributor,
            subject=self.subject,
            description=self.description,
            creator=self.creator,
            source=self.source,
            language=self.language,
            actionPlatform=self.action_platform,
            contentType=[self.content_type],
            encodingType=[self.encoding_type])

        response = trompace.connection.submit_query(qry, auth_required=self.authenticate)
        self.entrypoint_id = response['data']['CreateEntryPoint']['identifier']
        self.config_parser['EntryPoint']['id'] = self.entrypoint_id

        qry = trompace.mutations.application.mutation_add_entrypoint_application(
            application_id=self.application_id,
            entrypoint_id=self.entrypoint_id)
        response = trompace.connection.submit_query(qry, auth_required=self.authenticate)

        qry = trompace.mutations.controlaction.mutation_add_entrypoint_controlaction(
            entrypoint_id=self.entrypoint_id,
            controlaction_id=self.controlaction_id)
        response = trompace.connection.submit_query(qry, auth_required=self.authenticate)

        for i in range(self.inputs_n):
            label = 'Input{}'.format(i + 1)
            qry = trompace.mutations.property.mutation_create_property(
                title=self.inputs[label].title,
                name=self.inputs[label].name,
                description=self.inputs[label].description,
                rangeIncludes=self.inputs[label].rangeIncludes)

            resp = trompace.connection.submit_query(qry, auth_required=self.authenticate)
            self.inputs[label].id = resp['data']['CreateProperty']['identifier']
            self.config_parser['Input'+str(i+1)]['id'] = self.inputs[label].id

            qry = trompace.mutations.controlaction.mutation_add_controlaction_object(
                self.controlaction_id, self.inputs[label].id)
            resp = trompace.connection.submit_query(qry, auth_required=self.authenticate)
            print(resp)

        for i in range(self.params_n):
            label = 'Param{}'.format(i + 1)
            qry = trompace.mutations.property.mutation_create_propertyvaluespecification(
                name=self.params[label].name,
                description=self.params[label].description,
                defaultValue=self.params[label].defaultValue,
                valueMaxLength=self.params[label].valueMaxLength,
                valueMinLength=self.params[label].valueMinLength,
                multipleValues=self.params[label].multipleValues,
                valueName=self.params[label].valueName,
                valuePattern=self.params[label].valuePattern,
                valueRequired=self.params[label].valueRequired)

            resp = trompace.connection.submit_query(qry, auth_required=self.authenticate)
            self.params[label].id = resp['data']['CreatePropertyValueSpecification']['identifier']
            qry = trompace.mutations.controlaction.mutation_add_controlaction_object(
                self.controlaction_id, self.params[label].id)
            self.config_parser['Param'+str(i+1)]['id'] = self.params[label].id

            # qry = trompace.mutations.controlaction.mutation_add_controlaction_object(
            #     self.controlaction_id, self.params[i].id)
            resp = trompace.connection.submit_query(qry, auth_required=self.authenticate)

        fp = open(self.application_config,'w')
        self.config_parser.write(fp)
        fp.close()

    def write_client_ini(self, out_fn):
        ''' write a config file to store all the information needed by the client application (control action, entry
         point, params
         '''

        config = configparser.ConfigParser()

        config['server'] = {}
        for key in self.connection_parser['server']:
            config['server'][key] = self.connection_parser['server'][key]

        config['auth'] = {}
        for key in self.connection_parser['auth']:
            config['auth'][key] = self.connection_parser['auth'][key]

        config['logging'] = {}
        for key in self.connection_parser['logging']:
            config['logging'][key] = self.connection_parser['logging'][key]


        config['application'] = {}
        config['application']['ca_id'] = self.controlaction_id
        config['application']['ep_id'] = self.entrypoint_id
        config['application']['params_n'] = str(self.params_n)
        config['application']['inputs_n'] = str(self.inputs_n)

        for i in range(self.params_n):
            label = 'Param{}'.format(i + 1)
            config['Param' + str(i + 1)] = {}
            config['Param' + str(i+1)]['name'] = self.params[label].name
            config['Param' + str(i + 1)]['description'] = self.params[label].description
            config['Param' + str(i + 1)]['defaultValue'] = self.params[label].defaultValue
            config['Param' + str(i + 1)]['valueMaxLength'] = str(self.params[label].valueMaxLength)
            config['Param' + str(i + 1)]['valueMinLength'] = str(self.params[label].valueMinLength)
            config['Param' + str(i + 1)]['multipleValues'] = str(self.params[label].multipleValues)
            config['Param' + str(i + 1)]['valueName'] = self.params[label].valueName
            config['Param' + str(i + 1)]['valuePattern'] = self.params[label].valuePattern
            config['Param' + str(i + 1)]['valueRequired'] = str(self.params[label].valueRequired)
            config['Param' + str(i + 1)]['id'] = str(self.params[label].id)
            config['Param' + str(i + 1)]['encrypted'] = str(self.params[label].encrypted)

        for i in range(self.inputs_n):
            label = 'Input{}'.format(i + 1)
            config['Input' + str(i + 1)] = {}
            config['Input'+str(i+1)]['title'] = self.inputs[label].title
            config['Input'+str(i+1)]['name'] = self.inputs[label].name
            config['Input'+str(i+1)]['description'] = self.inputs[label].description
            config['Input'+str(i+1)]['rangeIncludes'] = str(self.inputs[label].rangeIncludes)
            config['Input'+str(i+1)]['id'] = str(self.inputs[label].id)
            config['Input' + str(i + 1)]['encrypted'] = str(self.inputs[label].encrypted)

        for i in range(self.outputs_n):
            label = 'Output{}'.format(i + 1)
            config['Output' + str(i + 1)] = {}
            config['Output' + str(i + 1)]['name'] = self.outputs[label].name
            config['Output' + str(i + 1)]['description'] = self.outputs[label].description
            config['Output' + str(i + 1)]['defaultValue'] = self.outputs[label].defaultValue
            config['Output' + str(i + 1)]['valueMaxLength'] = str(self.outputs[label].valueMaxLength)
            config['Output' + str(i + 1)]['valueMinLength'] = str(self.outputs[label].valueMinLength)
            config['Output' + str(i + 1)]['multipleValues'] = str(self.outputs[label].multipleValues)
            config['Output' + str(i + 1)]['valueName'] = self.outputs[label].valueName
            config['Output' + str(i + 1)]['valuePattern'] = self.outputs[label].valuePattern
            config['Output' + str(i + 1)]['valueRequired'] = str(self.outputs[label].valueRequired)
            config['Output' + str(i + 1)]['encrypted'] = str(self.outputs[label].encrypted)

        with open(out_fn, 'w') as configfile:
            config.write(configfile)
        configfile.close()

    async def listen_requests(self,debug_flag):
    # it listen for new entry point subscriptions and executes some code

        self.websocket_host = trompace.config.config.websocket_host
        print(self.websocket_host)
        subscription = trompace.subscriptions.controlaction.subscription_controlaction(self.entrypoint_id)
        INIT_STR = """{"type":"connection_init","payload":{}}"""

       # self.websocket_port = "ws://api-test.trompamusic.eu//graphql"
       # async with websockets.connect(self.websocket_port, subprotocols=['graphql-ws']) as websocket:
     #   async with websockets.connect(self.websocket_port, subprotocols=['graphql-ws']) as websocket:
   #     self.websocket_port = "wss://api-test.trompamusic.eu/graphql"
        async with websockets.connect(self.websocket_host, subprotocols=['graphql-ws']) as websocket:

            await websocket.send(INIT_STR)
          #  await websocket.send(subscription)

            async for message in websocket:
                if message == """{"type":"connection_ack"}""":
                    is_ok = True
                    print("Ack recieved")
                    await websocket.send(tpl.tools.get_sub_dict(subscription))
                elif is_ok:
                    print("Message recieved, processesing")
                    messageString = json.loads(message)
                    print(messageString)
                    control_id = messageString["payload"]["data"]["ControlActionRequest"]["identifier"]
                    qry = trompace.queries.controlaction.query_controlaction(control_id)
                    request_data = trompace.connection.submit_query(qry, auth_required=False)
                    print(request_data)
                    params = tpl.tools.get_ca_params(request_data)
                    await self.execute_command(params, control_id, debug_flag)

                if not is_ok:
                    raise Exception("don't have an ack yet")

    async def download_files(self, params):
        for key in params.keys():
            value = params[key]
            isURL = validators.url(value)
            if isURL:
                basename = str(uuid.uuid4())
                local_fn = self.data_path + basename
                await trompace.connection.download_file(value,local_fn)
              #  params[key] = "/data/" + basename # docker filesystem
                params[key] = basename # docker filesystem

            print("ok")
        return params

    async def upload_file(self, fn):
        self.minioclient.fput_object("tpl", fn, self.data_path + "/" + fn)
        fileURI = self.s3_public_server + "tpl/" + fn
        return fileURI

    def create_command_dict(self, params):
        # create a dict() with all the commands parameters. For input and params, these will be read from the control
        # action. For the outputs these will be created on the fly

        command_dict = {}
        input_files = {}
        for key in params.keys():
            for i in range(self.inputs_n):
                label = 'Input{}'.format(i + 1)
                if self.inputs[label].argument == key:
                    command_dict[label] = key + " " + "/data/" + params[key] + " "
                    input_files[label] = self.data_path + params[key]
            for i in range(self.params_n):
                label = 'Param{}'.format(i + 1)
                if self.params[label].argument == key:
                    if params[key] in self.constants.keys():
                        command_dict[label] = key + " " + self.constants[params[key]] + " "
                    else:
                        command_dict[label] = key + " " + params[key] + " "

        output_files = []
        for i in range(self.outputs_n):
            label = 'Output{}'.format(i + 1)
            out_fn = str(uuid.uuid4())
            command_dict[label] = self.outputs[label].argument + " /data/" + out_fn
            output_files.append(out_fn)

        return [command_dict, input_files, output_files]


    async def execute_command(self, params, control_id, debug_flag):
        # update control_id status to running
        qry = trompace.mutations.controlaction.mutation_update_controlaction(control_id,
                                                                trompace.StringConstant("ActiveActionStatus"))
        trompace.connection.submit_query(qry, auth_required=self.authenticate)

        params = await self.download_files(params)
        param_dict, input_files, output_files = self.create_command_dict(params)
        for i in range(self.inputs_n):
            label = 'Input{}'.format(i+1)
            if self.inputs[label].encrypted:
                tpl.tools.decrypt_file(input_files[label], self.key, input_files[label])
        cmd_to_execute = self.command_line.format(**param_dict)

        if self.requires_docker:
            docker_cmd = "docker run -it -v " + self.data_path+":/data --rm " + cmd_to_execute
            if debug_flag:
                print(docker_cmd)
            else:
                os.system(docker_cmd)

            for o in range(self.outputs_n):
                # upload data to server
                output_uri = await self.upload_file(output_files[o])

                # create digital document
                qry = trompace.mutations.digitaldocument.mutation_create_digitaldocument(
                    title=self.application_name,
                    contributor=self.contributor,
                    creator=self.creator,
                    source=output_uri,
                    format_=self.outputs['Output{}'.format(o+1)].mimeType,
                    language="en"
                )
                resp = trompace.connection.submit_query(qry, auth_required=self.authenticate)
                identifier = resp['data']['CreateDigitalDocument']['identifier']

            #    link digital document to source
                qry = trompace.mutations.controlaction.mutation_addactioninterfance_result(self.controlaction_id,
                                                                                           identifier)
                resp = trompace.connection.submit_query(qry, auth_required=self.authenticate)

        # update control_id status to finished
        qry = trompace.mutations.controlaction.mutation_update_controlaction(control_id,
                                                                    trompace.StringConstant("CompletedActionStatus"))
        trompace.connection.submit_query(qry, auth_required=self.authenticate)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train LSTM Network')
    parser.add_argument('--force',  type=int, default=0) # force==1 if we want to create a new application node even if
    # it already exists
    parser.add_argument('--connection', type=str) # config of the ce
    parser.add_argument('--app', type=str) # config of the application
   # parser.add_argument('-app', type=str, default='../../config/unique2.ini') # config of the application

    parser.add_argument('--client', type=str)  # config of the client file
    parser.add_argument('--execute', type=str, default=1)  # config of the client file

    args = parser.parse_args()

    myApp = TPLapp(args.app, args.connection)

    if myApp.registered == False or args.force == 1:
        myApp.register()
    myApp.write_client_ini(args.client)

    asyncio.run(myApp.listen_requests(bool(args.execute)))
