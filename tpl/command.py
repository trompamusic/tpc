import trompace
import uuid
import os
import tpl.tools

def execute_command(tplObj, params, control_id, execute_flag, total_jobs):
    # update control_id status to running
    print("executing process for ", control_id)
    qry = trompace.mutations.controlaction.mutation_update_controlaction_status(control_id,
                                                            trompace.constants.ActionStatusType.ActiveActionStatus)
    trompace.connection.submit_query(qry, auth_required=tplObj.authenticate)

    params = tplObj.download_files(params)
    param_dict, input_files, output_files = tplObj.create_command_dict(params)
    for i in range(tplObj.inputs_n):
        label = 'Input{}'.format(i+1)
        if tplObj.inputs[label].encrypted:
            tplObj.tools.decrypt_file(input_files[label], tplObj.key, input_files[label])
    cmd_to_execute = tplObj.command_line.format(**param_dict)

    outputs_fn = str(uuid.uuid4()) + ".ini"
    if tplObj.requires_docker:
        docker_cmd = "docker run -it -v " + tplObj.data_path+":/data --rm " + cmd_to_execute + ' --tpl_out /data/' + \
                     outputs_fn
        if execute_flag:
            os.system(docker_cmd)
        else:
            print(docker_cmd)
            for o in range(tplObj.outputs_n):
                fp = open(tplObj.data_path + output_files[o], 'w')
                fp.close()

        config_outputs_fn = tplObj.configparser.ConfigParser()
        config_outputs_fn.read(tplObj.data_path+outputs_fn)

        for o in range(tplObj.outputs_n):
            # upload data to server
            argument = tplObj.outputs['Output{}'.format(o+1)].argument[2::]
            if config_outputs_fn.has_option('tplout', argument):
                output_files[o] = os.path.basename(config_outputs_fn['tplout'][argument])
            output_uri = tplObj.upload_file(output_files[o])

            # create digital document
            qry = trompace.mutations.digitaldocument.mutation_create_digitaldocument(
                title=tplObj.application_name,
                contributor=tplObj.contributor,
                creator=tplObj.creator,
                source=output_uri,
                format_=tplObj.outputs['Output{}'.format(o+1)].mimeType,
                language="en",
                description=tplObj.outputs['Output{}'.format(o+1)].argument
            )
            resp = trompace.connection.submit_query(qry, auth_required=tplObj.authenticate)
            identifier = resp['data']['CreateDigitalDocument']['identifier']

        #    link digital document to source
            qry = trompace.mutations.controlaction.mutation_add_actioninterface_result(control_id,
                                                                                       identifier)
            resp = trompace.connection.submit_query(qry, auth_required=tplObj.authenticate)

    # update control_id status to finished
    qry = trompace.mutations.controlaction.mutation_update_controlaction_status(control_id,
                                                            trompace.constants.ActionStatusType.CompletedActionStatus)

    trompace.connection.submit_query(qry, auth_required=tplObj.authenticate)
    print("process for ", control_id, " finished")
    total_jobs.value -= 1