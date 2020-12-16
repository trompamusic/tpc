# TROMPA Processing Library

Aggelos Gkiokas (aggelos.gkiokas@upf.edu)

## Overview

This repo contains two main programs:
- The TROMPA Processing Library (TPL) which a software that automatically triggers the algorithms and handles all the communication with the CE. Currently, for each algorithm an instance of the TPL must be invoked.
- The client library: it is a helper program provides an interface to create and (or) execute queries.


## Installation
pip install -r requirements.txt
pip install git+https://github.com/aggelosgkiokas/tpl.git

## Processing Library 

To invoke one the TPL for a specific algorithm/software one has to run the following:

python  application.py --ce ce_config_file --app app_config_file --client --clinet_confif_file --force (optional)

ce_config_file: configuration file containing information about CE connection

app_config_file: configuration file containing information about the program

client_file: a client configuration file created by the TPL of the client software. It describes the input/output/parameter of a specific algorithm

force: (0 or 1) a flag inficating that the app will be registered to the CE even if it has been done before (creates a new application/entry point/control action nodes)

execute: (0 or 1) a flag indicating if the algorithm will be executed or not (display only the command)
Examples of the configuration files can be found in the ./config/ folder

###Note:
In order to run the docker commands (algorithms) TPL should be run as root
## Processing Library Client

To invoke one the TPL for a specific algorithm/software one has to run the following:

--client_ini client.ini --inputs {a list of inputs} --params {a list of params} 

e.g.

python client.py --client_ini client.ini --inputs 5ea78f18-8f12-46e0-ba38-582e254d4de7 5d6fadc9-0a32-4692-af44-afc0b692bafd -params 1 28 0.460487499990472 Soprano

