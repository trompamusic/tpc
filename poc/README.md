# TROMPA Processing Library Proof of Concept

Aggelos Gkiokas (aggelos.gkiokas@upf.edu)

## Overview

This folder contains a generic proof of concept algorithm. It contains the following files:
- poc.py: the Proof of Concept Algorithm. This algorithms takes 4 inputs, 2 parameters and creates 3 files.
    - Input 1: a CE node file stored in a public URI
    - Input 2: a CE node file stored in a private solidpod
    - Input 3: the identifier of a CE node
    - Input 3: the URI of a CE node
    - Param 1: a random string parameter
    - Param 2: a random string parameter
    - Output 1: the 1st output
    - Output 2: the 2nd output
    - Output 3: the 3rd output 
    
The POC algorithm does the following: it copies Input1 and Input 2 to Outputs 1 & 2 respectively, and stored a text file on Output3 containing Input3, Input4, Param1, Param2 information. This POC algorithm exploits all TPL capabilities (i.e. getting the CE node file source, the identifier of a node or the URI that corresponds to a CE node)
      

- poc.ini: the configuration file in order to load the algorithm to the TPL
- Dockerfile: a docker file containing the poc.py algorithm


### Example of server information file

Server information must be passed as an encrypted string. In this string, each line contains the information for each output.

solidpod;https://trompa-solid.upf.edu;https://agkiokas2.trompa-solid.upf.edu/profile/card#me;https://agkiokas2.trompa-solid.upf.edu/private;1
solidpod;https://trompa-solid.upf.edu;https://agkiokas2.trompa-solid.upf.edu/profile/card#me;https://agkiokas2.trompa-solid.upf.edu/private;0
s3;1

the first value indicates if it's a solidpod; The 2nd is the solidpod host; The 3rd is the solidpod user; The 4th is the solidpod folder to be saved;the 5th is if we want the TPL to encrypt the URI;
