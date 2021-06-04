import configparser
import asyncio
import subprocess

import websockets
import types
import json
import argparse
import uuid
import minio
import tpl.tools
import os
import sys
import requests
import urllib

import trompace
import trompace.config
import trompace.constants
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
import trompasolid.client

import validators
'''Script of the TROMPA Processing Library class.
'''


class TPLapp:
    def __init__(self, application_config, ce_config, tpl_params):

        '''
        the class constructor reads the application configuration file and the ce configuration file, stores all the
        needed and also initializes the ce-client connection
        '''

        # create a CE connection
        self.ce_config = ce_config
        self.application_config = application_config

        trompace.config.config.load(ce_config)

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
            self.application_id = None
            self.registered = False

        self.language = self.config_parser['Application']['language']
        self.temporary_data_path = tpl_params['temporary_data_path']
        self.permanent_data_path = tpl_params['permanent_data_path']



        self.control_action = self.config_parser['ControlAction']['name']
        self.inputs_n = int(self.config_parser['ControlAction']['num_inputs'])
        self.params_n = int(self.config_parser['ControlAction']['num_params'])
        self.outputs_n = int(self.config_parser['ControlAction']['num_outputs'])

        self.controlaction_id = None
        if self.config_parser.has_option('ControlAction', 'id'):
            self.controlaction_id = self.config_parser['ControlAction']['id']

        self.content_type = self.config_parser['EntryPoint']['content_type']
        self.encoding_type = self.config_parser['EntryPoint']['encoding_type']
        self.action_platform = self.config_parser['EntryPoint']['action_platform']
        self.entrypoint_id = None
        if self.config_parser.has_option('EntryPoint', 'id'):
            self.entrypoint_id = self.config_parser['EntryPoint']['id']
        self.requires_docker = self.config_parser.getboolean('EntryPoint', 'requires_docker')
        self.command_line = self.config_parser['EntryPoint']['command_line']
        self.docker_image = self.config_parser['EntryPoint']['docker_image']

        # load connection/secutiry information
        self.encrypt_fn = self.connection_parser.get('tplKey', 'keyFile')
        self.s3_secure = self.connection_parser.getboolean('s3', 'secure')
        self.s3_key = self.connection_parser.get('s3', 'access_key')
        self.s3_secret = self.connection_parser.get('s3', 'secret_key')
        self.s3_server = self.connection_parser.get('s3', 'server')
        self.s3_public_server = self.connection_parser.get('s3', 'public_server')

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
        self.identifier_to_label = {}

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
                self.identifier_to_label[input_property.id] = label

            input_property.argument = input_property.name
            input_property.encrypted = property.getboolean('encrypted')
            input_property.field = property['field']
            self.inputs[label] = input_property
            self.params[label] = input_property
            self.inputs[input_property.title] = label

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
                self.identifier_to_label[param_property.id] = label

            param_property.encrypted = property.getboolean('encrypted')
            param_property.argument = param_property.valueName
            param_property.field = property['field']

            self.params[label] = param_property

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
            param_property.extension = property.get('extension')
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

        response = trompace.connection.submit_query(qry, auth_required=True)

        self.application_id = response['data']['CreateSoftwareApplication']['identifier']
        self.config_parser['Application']['id'] = self.application_id

        qry = trompace.mutations.controlaction.mutation_create_controlaction(name=self.control_action,
                                                                             description=self.description)
        response = trompace.connection.submit_query(qry, auth_required=True)
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

        response = trompace.connection.submit_query(qry, auth_required=True)
        self.entrypoint_id = response['data']['CreateEntryPoint']['identifier']
        self.config_parser['EntryPoint']['id'] = self.entrypoint_id

        qry = trompace.mutations.application.mutation_add_entrypoint_application(
            application_id=self.application_id,
            entrypoint_id=self.entrypoint_id)
        response = trompace.connection.submit_query(qry, auth_required=True)

        qry = trompace.mutations.controlaction.mutation_add_entrypoint_controlaction(
            entrypoint_id=self.entrypoint_id,
            controlaction_id=self.controlaction_id)
        response = trompace.connection.submit_query(qry, auth_required=True)

        for i in range(self.inputs_n):
            label = 'Input{}'.format(i + 1)
            qry = trompace.mutations.property.mutation_create_property(
                title=self.inputs[label].title,
                name=self.inputs[label].name,
                description=self.inputs[label].description,
                rangeIncludes=[self.inputs[label].rangeIncludes])

            resp = trompace.connection.submit_query(qry, auth_required=True)
            self.inputs[label].id = resp['data']['CreateProperty']['identifier']
            self.config_parser['Input'+str(i+1)]['id'] = self.inputs[label].id

            qry = trompace.mutations.controlaction.mutation_add_controlaction_object(
                self.controlaction_id, self.inputs[label].id)
            resp = trompace.connection.submit_query(qry, auth_required=True)
            self.identifier_to_label[self.inputs[label].id] = label

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

            resp = trompace.connection.submit_query(qry, auth_required=True)
            self.params[label].id = resp['data']['CreatePropertyValueSpecification']['identifier']
            qry = trompace.mutations.controlaction.mutation_add_controlaction_object(
                self.controlaction_id, self.params[label].id)
            self.config_parser['Param'+str(i+1)]['id'] = self.params[label].id

            # qry = trompace.mutations.controlaction.mutation_add_controlaction_object(
            #     self.controlaction_id, self.params[i].id)
            resp = trompace.connection.submit_query(qry, auth_required=True)
            self.identifier_to_label[self.params[label].id] = label

        with open(self.application_config, 'w') as fp:
            self.config_parser.write(fp)

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
            config['Output' + str(i + 1)]['extension'] = str(self.outputs[label].extension)

        with open(out_fn, 'w') as configfile:
            config.write(configfile)
        configfile.close()

    async def download_files_async(self, params):
        for i in range(self.inputs_n):
            # download only if it's input
            label = "Input{}".format(i + 1)
            if self.inputs[label].field == 'source':
                source = params[label]
                basename = str(uuid.uuid4())
                _, file_extension = os.path.splitext(source)
                local_fn = os.path.join(self.temporary_data_path, basename) + file_extension
                trompace.connection.download_file_async(source, local_fn)
                #     print(os.path.exists(local_fn))
                params[label] = basename + file_extension  # docker filesystem
        return params

    def download_files(self, params):
        for i in range(self.inputs_n):
            # download only if it's input
            label = "Input{}".format(i + 1)
            if self.inputs[label].field == 'source':
                source = params[label]
                basename = str(uuid.uuid4())
                _, file_extension = os.path.splitext(source)
                local_fn = os.path.join(self.temporary_data_path, basename) + file_extension

           #     trompace.connection.download_file(source, local_fn)

                if tpl.tools.check_if_uri_is_solid_pod(source):
                    tpl.tools.download_from_solid_pod(source)
                else:
                    trompace.connection.download_file(source, local_fn)
              #   try:
              #
              #   except requests.exceptions.HTTPError:
              #       tpl.tools.download_from_solid_pod(source)
              # #      trompace.connection.download_file(source, local_fn)
              #   else:
              #       print("Unexpected error:", sys.exc_info()[0])

                # except Exception as e:
                #     print(e)
                #     trompace.connection.download_file(source, local_fn)
                # else:
                #     print("Unexpected error:", sys.exc_info()[0])
                #     print("could not download file")
                #     print(os.path.exists(local_fn))
                params[label] = basename + file_extension  # docker filesystem
        return params

    async def upload_file_async(self, fn):
        self.minioclient.fput_object("tpl", fn, os.path.join(self.temporary_data_path, fn))
        fileURI = self.s3_public_server + "tpl/" + fn
        return fileURI

    def upload_file(self, server_url, fn):
        if server_url == "TPL":
            self.minioclient.fput_object("tpl", fn, os.path.join(self.temporary_data_path, fn))
            fileURI = self.s3_public_server + "tpl/" + fn
        elif tpl.tools.check_if_uri_is_solid_pod(server_url):
            fileURI = ""

        return fileURI

    def upload_solidpod(self, solid_pod_uri):
        solid_client = trompasolid.client
        solid_client.init_redis()

        bearer = solid_client.get_bearer_for_user("https://trompa-solid.upf.edu",
                                            "https://agkiokas.trompa-solid.upf.edu/profile/card#me")

        r = requests.put("https://agkiokas.trompa-solid.upf.edu/testfile.txt",
                         data="this is the contents to add to the file",
                         headers={"authorization": "Bearer %s" % bearer, "content-type": "text/plain"})

    def download_from_solid_pod(self, uri, out_filename):

        solid_client = trompasolid.client
        solid_client.init_redis()
        urlParseResult = urllib.parse.urlparse(uri)
        pos = urlParseResult.netloc.find(".")

        host = urlParseResult.scheme + "://" + urlParseResult.netloc[pos + 1::]

        bearer = solid_client.get_bearer_for_user(host, "https://agkiokas2.trompa-solid.upf.edu/profile/card#me")

        r = requests.get(uri, headers={"authorization": "Bearer %s" % bearer})

        return r.content
    async def listen_requests(self,execute_flag=False):
    # it listen for new entry point subscriptions and executes some code

        self.websocket_host = trompace.config.config.websocket_host
        print(self.websocket_host)
        subscription = trompace.subscriptions.controlaction.subscription_controlaction(self.entrypoint_id)
        INIT_STR = """{"type":"connection_init","payload":{}}"""
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
                    await self.execute_command(params, control_id, execute_flag)

                if not is_ok:
                    raise Exception("don't have an ack yet")


    def create_command_dict(self, params):
        # create a dict() with all the commands parameters. For input and params, these will be read from the control
        # action. For the outputs these will be created on the fly

        command_dict = {}
        input_files = {}

        for i in range(self.inputs_n):
            label = 'Input{}'.format(i + 1)
            if self.inputs[label].field == 'source':
                command_dict[label] = "/data/" + params[label] + " "
                input_files[label] = os.path.join(self.temporary_data_path, params[label])

        for i in range(self.params_n):
            label = 'Param{}'.format(i + 1)
            command_dict[label] = params[label]
            if params[label] in self.constants.keys():
                params[label] = self.constants[params[label]]

                # if self.params[label].argument == key:
                #     if params[key] in self.constants.keys():
                #         command_dict[label] = key + " " + self.constants[params[key]] + " "
                #     else:
                #         command_dict[label] = key + " " + params[key] + " "

        # for i in range(self.params_n):
        #     label = 'Param{}'.format(i + 1)
        #     if self.params[label].argument == key:
        #         if params[key] in self.constants.keys():
        #             command_dict[label] = key + " " + self.constants[params[key]] + " "
        #         else:
        #             command_dict[label] = key + " " + params[key] + " "
        # for key in params.keys():
        #     for i in range(self.inputs_n):
        #         label = 'Input{}'.format(i + 1)
        #         if self.inputs[label].field == 'source':
        #             command_dict[label] = "/data/" + params[key] + " "
        #             input_files[label] = os.path.join(self.temporary_data_path, params[key])


        output_files = []
        for i in range(self.outputs_n):
            label = 'Output{}'.format(i + 1)
            out_fn = str(uuid.uuid4())
            command_dict[label] = " /data/" + out_fn + "." + self.outputs[label].extension
            output_files.append(os.path.join(self.temporary_data_path, out_fn + "." + self.outputs[label].extension))

        return [command_dict, input_files, output_files]


    def execute_command(self, params, control_id, execute_flag, total_jobs):
        # update control_id status to running
        xxx=0
        print("authentication: ", params['Param'+str(self.params_n)])
       # authentication_data = json.loads(params['Param'+str(self.params_n-1)])


        application_permanent_path = os.path.join(self.permanent_data_path, self.application_id)
        os.makedirs(application_permanent_path, exist_ok=True)

        print("PID: ", os.getpid(), "executing ", control_id)
        try:
            qry = trompace.mutations.controlaction.mutation_update_controlaction_status(control_id,
                                                                    trompace.constants.ActionStatusType.ActiveActionStatus)
            trompace.connection.submit_query(qry, auth_required=True)
         #   print('updating ca status')
            params = self.download_files(params)
         #   print('downloaded file')

            param_dict, input_files, output_files = self.create_command_dict(params)
         #   print('updated params')

            output_storages = param_dict['Param'+str(self.params_n)]
            output_storages = output_storages.split(',')
            for i in range(self.inputs_n):
                label = 'Input{}'.format(i+1)
                if self.inputs[label].encrypted:
                    try:
                        tpl.tools.decrypt_file(input_files[label], self.key, input_files[label])
                    except :
                        print("Unexpected error:", sys.exc_info()[0])

            cmd_to_execute = self.command_line.format(**param_dict)
         #   print('created command')

            outputs_fn = str(uuid.uuid4()) + ".ini"
            if self.requires_docker:
                command_args = [
                    "docker", "run", "--rm", "-it",
                    "-v", self.temporary_data_path + ":/data", "-e", "TPL_WORKING_DIRECTORY=/data",
                    "-v", application_permanent_path + ":/storage", "-e", "TPL_INTERNAL_DATA_DIRECTORY=/storage",
                    self.docker_image
                ] + cmd_to_execute.split()

                if execute_flag:
                    subprocess.run(command_args)
                else:
                    print(" ".join(command_args))
                    for o in range(self.outputs_n):
                        fp = open(output_files[o], 'w')
                        fp.close()

                config_outputs_fn = configparser.ConfigParser()
                config_outputs_fn.read(os.path.join(self.temporary_data_path, outputs_fn))
           #     print('saving outputs')

                for o in range(self.outputs_n):
                    # upload data to server
                    argument = self.outputs['Output{}'.format(o+1)].argument[2::]
                    if config_outputs_fn.has_option('tplout', argument):
                        output_files[o] = os.path.basename(config_outputs_fn['tplout'][argument])
                    output_uri = self.upload_file(output_files[o])

                    # create digital document
                    qry = trompace.mutations.digitaldocument.mutation_create_digitaldocument(
                        title=self.application_name,
                        contributor=self.contributor,
                        creator=self.creator,
                        source=output_uri,
                        format_=self.outputs['Output{}'.format(o+1)].mimeType,
                        language="en",
                        description=self.outputs['Output{}'.format(o+1)].argument
                    )
                    resp = trompace.connection.submit_query(qry, auth_required=True)
                    identifier = resp['data']['CreateDigitalDocument']['identifier']

                #    link digital document to source
                    qry = trompace.mutations.controlaction.mutation_add_actioninterface_result(control_id,
                                                                                               identifier)
                    resp = trompace.connection.submit_query(qry, auth_required=True)

            # update control_id status to finished
            qry = trompace.mutations.controlaction.mutation_update_controlaction_status(control_id,
                                                                    trompace.constants.ActionStatusType.CompletedActionStatus)

            trompace.connection.submit_query(qry, auth_required=True)
        except:
            print("Error:", sys.exc_info()[0], " for ca_id", control_id)
            qry = trompace.mutations.controlaction.mutation_update_controlaction_status(control_id,
                                                                    trompace.constants.ActionStatusType.FailedActionStatus)
            trompace.connection.submit_query(qry, auth_required=True)

        # print('updating ca status')
        total_jobs.value -= 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trompa Processing Library')
    parser.add_argument('--force', action='store_true',
                        help='Set if you want to create a new application node even if one exists')
    parser.add_argument('--connection', type=str, help='CE config file', required=True)
    parser.add_argument('--app', type=str, help='Application config file', required=True)

    parser.add_argument('--client', type=str, help="config of the client file", required=True)
    parser.add_argument('--execute', action='store_true', help='Execute the algorithm listed in the application config file')

    args = parser.parse_args()

    myApp = TPLapp(args.app, args.connection)

    if not myApp.registered or args.force:
        myApp.register()
    myApp.write_client_ini(args.client)

    asyncio.run(myApp.listen_requests(args.execute))
