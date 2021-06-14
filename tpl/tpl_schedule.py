import configparser
import argparse
import tpl.application
import glob
import asyncio
import trompace.queries.templates
import trompace.config
import multiprocessing
import tpl.command
import time
import os
import numpy
import tpl.trigger

class TPLschedule():
    def __init__(self, tpl_config, register, execute):
        self.tpl_config = tpl_config
        self.applications = []
        self.applications_n = 0
        self.applications_config = []
        self.job_list = []
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(tpl_config)

        self.applications_folder = self.config_parser['tpl']['application_folder']
        self.low_processes = int(self.config_parser['processes']['low_priority'])
        self.medium_processes = int(self.config_parser['processes']['medium_priority'])
        self.high_processes = int(self.config_parser['processes']['high_priority'])
        self.max_processes = int(self.config_parser['processes']['max_processes'])
        self.client_folder = self.config_parser['tpl']['client_folder']
        self.temporary_data_path = self.config_parser['tpl']['temporary_storage']
        if not os.path.isabs(self.temporary_data_path):
            self.temporary_data_path = os.path.abspath(self.temporary_data_path)
        self.permanent_data_path = self.config_parser['tpl']['permanent_storage']
        if not os.path.isabs(self.permanent_data_path):
            self.permanent_data_path = os.path.abspath(self.permanent_data_path)


        self.connection_ini = self.config_parser['connection']['config_file']

        self.control_actions = []
        trompace.config.config.load(self.connection_ini)
        self.applications_map = {}

        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(tpl_config)

        self.tpl_params = {}
        self.tpl_params['temporary_data_path'] = self.temporary_data_path
        self.tpl_params['permanent_data_path'] = self.permanent_data_path

        files = glob.glob(self.applications_folder + "*.ini")
        for i,f in zip(range(len(files)), files):
            self.applications_config.append(f)
            myApp = tpl.application.TPLapp(f, self.connection_ini, self.tpl_params)

#            myApp = tpl.application.TPLapp(self.applications_config[i], self.ce_config)
            if register:
               myApp.register()

            myApp.write_client_ini(self.client_folder+"//"+myApp.application_name.replace(' ', '_') + ".ini")
            self.applications.append(myApp)
            self.applications_map[myApp.controlaction_id] = myApp
            self.control_actions.append(myApp.controlaction_id)
        self.applications_n = len(files)
        print(self.applications_n, " applications added..")
        self.active_jobs = multiprocessing.Value('i', 0)
        self.execute = execute
    def poll(self):
        args = {}
        filter = {}
        filter['actionStatus'] = trompace.StringConstant("PotentialActionStatus")
        ca_list = []
        for ca in self.control_actions:
            ca_list.append({"identifier":ca})
        filter['wasDerivedFrom_in'] = ca_list
        args['filter'] = filter
        qry = trompace.queries.templates.format_query("ControlAction",args,["identifier", "wasDerivedFrom{identifier}"])
        response = trompace.connection.submit_query(qry, auth_required=False)
        pending_jobs = response['data']['ControlAction']
        pending_jobs_n = len(pending_jobs)
        priorities = numpy.zeros((pending_jobs_n,))

        for j in range(pending_jobs_n):
            template_ca_id = pending_jobs[j]['wasDerivedFrom'][0]['identifier']
            priorities[j] = self.applications_map[template_ca_id].priotity

        ids = numpy.argsort(priorities)
    #    print(pending_jobs)
        jobs_to_run = min(self.max_processes - self.active_jobs.value, pending_jobs_n)
    #    print(str(time.time()) + " : " + str(jobs_to_run) + " jobs are running")

        # update the status of the ca that will be run in this poll
        for j in range(jobs_to_run):
            ca_id = pending_jobs[ids[j]]['identifier']
            qry = trompace.mutations.controlaction.mutation_update_controlaction_status(ca_id,
                                                                    trompace.constants.ActionStatusType.ActiveActionStatus)
            trompace.connection.submit_query(qry, auth_required=True)

        for j in range(jobs_to_run):
            ca_id = pending_jobs[ids[j]]['identifier']
         #   print(ca_id)
            qry = trompace.queries.controlaction.query_controlaction(ca_id)
            request_data = trompace.connection.submit_query(qry, auth_required=False)
            source_ca_id = request_data['data']['ControlAction'][0]['wasDerivedFrom'][0]['identifier']
            app2run = self.applications_map[source_ca_id]
            params = tpl.tools.get_ca_params(request_data, app2run)

            self.active_jobs.value += 1
            kwargs = {}
            kwargs['params'] = params
            kwargs['control_id'] = ca_id
            kwargs['execute_flag'] = self.execute
            kwargs['total_jobs'] = self.active_jobs
        #    app2run.execute_command(params=params,control_id=ca_id, execute_flag=True, total_jobs = self.active_jobs)
           # params, control_id, execute_flag
            p = multiprocessing.Process(target=app2run.execute_command, kwargs=kwargs)
            p.start()


#Async queue
#https://docs.python.org/3/library/asyncio-queue.html

#async vs que
# https://leimao.github.io/blog/Python-Concurrency-High-Level/
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='TROMPA Processing Library')

    parser.add_argument('--tpl_config', type=str)  # config of the ce
    parser.add_argument('--register', type=int, default=0)
    parser.add_argument('--exec', type=int, default=0)


    args = parser.parse_args()
    myTPL = TPLschedule(args.tpl_config, bool(args.register), bool(args.exec))

   # asyncio.run(trigger.run("MediaObject"))
    #asyncio.run(trigger.run("AudioObject"))

    while True:
        myTPL.poll()
        time.sleep(1)
