import configparser
import argparse
import tpl.application
import glob
import asyncio
import trompace.queries.templates
import trompace.config




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


        files = glob.glob(self.applications_folder + "*.ini")
        for i,f in zip(range(len(files)), files):
            self.applications_config.append(f)
            myApp = tpl.application.TPLapp(self.applications_config[i], self.ce_config)
        #    myApp.register()
            myApp.write_client_ini(self.client_folder+"//"+str(i)+".ini")
            self.applications.append(myApp)
            self.control_actions.append(myApp.controlaction_id)
        self.applications_n = len(files)
        print(self.applications_n, " applications added..")

    def poll(self):
        print("hello")
        args = {}
        filter = {}
        filter['actionStatus'] = trompace.StringConstant("PotentialActionStatus")
        ca_list = []
        for ca in self.control_actions:
            ca_list.append({"identifier":ca})
        filter['wasDerivedFrom_in'] = ca_list
        args['filter'] = filter
        qry = trompace.queries.templates.format_query("ControlAction",args,["identifier"])

        print(qry)

#Async queue
#https://docs.python.org/3/library/asyncio-queue.html

#async vs que
# https://leimao.github.io/blog/Python-Concurrency-High-Level/
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='TROMPA Processing Library')

    parser.add_argument('--tpl_config', type=str)  # config of the ce

    args = parser.parse_args()

    myTPL = TPLschedule(args.tpl_config)
    myTPL.poll()
   # asyncio.run(myTPL.run())
