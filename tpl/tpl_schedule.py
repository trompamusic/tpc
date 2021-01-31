import configparser
import argparse
import tpl.application

class TPLschedule():
    def __init__(self, tpl_config, ce_config):
        self.ce_config = ce_config
        self.tpl_config = tpl_config
        self.applications = []
        self.applications_n = 0
        self.applications_config = []
        self.job_list = []
        self.jobs_n

    def run(self):
        print("running")

        for i in range(self.applications_n):
            myApp = tpl.application.TPLapp(self.applications_config[i], self.ce_config)

#Async queue
#https://docs.python.org/3/library/asyncio-queue.html

#async vs que
# https://leimao.github.io/blog/Python-Concurrency-High-Level/
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='TROMPA Processing Library')

    parser.add_argument('--connection', type=str)  # config of the ce
    parser.add_argument('--config', type=str)  # config of the tpl

    args = parser.parse_args()

    myTPL = TPLschedule(args.config, args.connection)

