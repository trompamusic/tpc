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

class TPLschedule():
    def __init__(self, tpl_config):
        self.tpl_config = tpl_config
        self.applications = []
        self.applications_n = 0
        self.applications_config = []
        self.job_list = []
        self.config_parser = configparser.ConfigParser()
        self.config_parser.read(tpl_config)
        self.applications_folder = self.config_parser['tpl']['application_folder']
        self.max_processes = int(self.config_parser['tpl']['max_processes'])
        self.ce_config = self.config_parser['tpl']['ce_config']
        self.client_folder = self.config_parser['tpl']['client_folder']
        self.control_actions = []
        trompace.config.config.load(self.ce_config)
        self.applications_map = {}


        files = glob.glob(self.applications_folder + "*.ini")
        for i,f in zip(range(len(files)), files):
            self.applications_config.append(f)
            myApp = tpl.application.TPLapp(self.applications_config[i], self.ce_config)
          #  myApp.register()
            myApp.write_client_ini(self.client_folder+"//"+str(i)+".ini")

            self.applications.append(myApp)
            self.applications_map[myApp.controlaction_id] = myApp
            self.control_actions.append(myApp.controlaction_id)
        self.applications_n = len(files)
        print(self.applications_n, " applications added..")
        self.active_jobs = multiprocessing.Value('i', 0)

    def poll(self):
        args = {}
        filter = {}
        filter['actionStatus'] = trompace.StringConstant("PotentialActionStatus")
        ca_list = []
        for ca in self.control_actions:
            ca_list.append({"identifier":ca})
        filter['wasDerivedFrom_in'] = ca_list
        args['filter'] = filter
        qry = trompace.queries.templates.format_query("ControlAction",args,["identifier"])
        response = trompace.connection.submit_query(qry, auth_required=False)
        pending_jobs = response['data']['ControlAction']
        pending_jobs_n = len(pending_jobs)
        jobs_to_run = min(self.max_processes - self.active_jobs.value, pending_jobs_n)
    #    print(str(time.time()) + " : " + str(jobs_to_run) + " jobs are running")
        for j in range(jobs_to_run):
            ca_id = pending_jobs[j]['identifier']
            print(ca_id)
            qry = trompace.queries.controlaction.query_controlaction(ca_id)
            request_data = trompace.connection.submit_query(qry, auth_required=False)
            source_ca_id = request_data['data']['ControlAction'][0]['wasDerivedFrom'][0]['identifier']
            params = tpl.tools.get_ca_params(request_data)
            app2run = self.applications_map[source_ca_id]
            self.active_jobs.value += 1
            kwargs = {}
            kwargs['tplObj'] = app2run
            kwargs['params'] = params
            kwargs['control_id'] = ca_id
            kwargs['execute_flag'] = False
            kwargs['total_jobs'] = self.active_jobs

            params, control_id, execute_flag
            p = multiprocessing.Process(target=tpl.command.execute_command, kwargs=kwargs)
            p = multiprocessing.Process(target=app2run.execute_command, kwargs=kwargs)
            p.start()


#Async queue
#https://docs.python.org/3/library/asyncio-queue.html

#async vs que
# https://leimao.github.io/blog/Python-Concurrency-High-Level/
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='TROMPA Processing Library')

    parser.add_argument('--tpl_config', type=str)  # config of the ce

    args = parser.parse_args()

    myTPL = TPLschedule(args.tpl_config)
    while True:
        myTPL.poll()
        time.sleep(1)

   # asyncio.run(myTPL.run())
