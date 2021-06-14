import trompace
import trompace.config
import trompace.connection
import trompace.subscriptions
import trompace.subscriptions.controlaction
import trompace.subscriptions.templates
import trompace.subscriptions.mediaobject
import trompace.subscriptions.audioobject
import trompace.queries.mediaobject
import trompace.queries.audioobject
import os
import websockets
import tpl.tools
import json
import argparse
import asyncio
import tpl.client

class Triggerer():
    def __init__(self, trigger_config, ce_config):
        self.type_to_app = {}
        self.node_types = ["AudioObject", "MediaObject", "VideoObject"]
        for type in self.node_types:
            self.type_to_app[type] = {}
        fp = open(trigger_config,'r')
        lines = fp.readlines()
        for line in lines:
            parts = line.split(';')

            node_type, extension, ini_file = parts[0:3]
            if len(parts) > 3:
                params = parts[3::]
            else:
                params = []
            client = tpl.client.TPLclient(ini_file, ce_config)

            clientObject = {}
            clientObject['client'] = client
            clientObject['params'] = params

            if extension in self.type_to_app[node_type]:
                self.type_to_app[node_type][extension].append(clientObject)
            else:
                self.type_to_app[node_type][extension] = [clientObject]

        trompace.config.config.load(ce_config)
        print("done")

    def batch(self, node_type):
        if node_type == "MediaObject":
            qry = trompace.queries.mediaobject.query_mediaobject(return_items=["contentUrl", "identifier"])
            request_data = trompace.connection.submit_query(qry, auth_required=False)
            objects = request_data['data'][node_type]
            actions_n = len(objects)
            for object in objects:
                print(object)
                contentUrl = object['contentUrl']
                identifier = object['identifier']
                if contentUrl is not None:
                    filename, file_extension = os.path.splitext(contentUrl)
                    file_extension = file_extension[1::]
                    #   extension = contentUrl((contentUrl.lastIndexOf(".") + 1):-1)

                    if file_extension in self.type_to_app[node_type]:
                        actions = self.type_to_app[node_type][file_extension]

                    for action in actions:
                        client = action['client']
                        storage = action['storage_file']
                        params = action['params']
                        qry = client.send_request([identifier], params, storage, execute=False)
                        print(qry)

    async def run(self, node_type):
        self.websocket_host = trompace.config.config.websocket_host
        print(self.websocket_host)
        if node_type == "MediaObject":
            subscription = trompace.subscriptions.mediaobject.subscription_media_object()
        elif node_type == "AudioObject":
            subscription = trompace.subscriptions.audioobject.subscription_audio_object()

        INIT_STR = """{"type":"connection_init","payload":{}}"""
        async with websockets.connect(self.websocket_host, subprotocols=['graphql-ws']) as websocket:

            await websocket.send(INIT_STR)
          #  await websocket.send(subscription)

            async for message in websocket:
                if message == """{"type":"connection_ack"}""":
                    is_ok = True
                    print("Ack recieved")
                   # await websocket.send(tpl.tools.get_sub_dict(subscription))
                    await websocket.send(tpl.tools.get_sub_dict(subscription))

                elif is_ok:
                    print("Message recieved, processesing")
                    messageString = json.loads(message)
                    print(messageString)
                    if node_type == "MediaObject":
                        identifier = messageString["payload"]["data"]["MediaObjectCreateMutation"]["identifier"]
                        qry = trompace.queries.mediaobject.query_mediaobject(
                            identifier=identifier,
                            return_items=["contentUrl"]
                        )
                    elif node_type == "AudioObject":
                        identifier = messageString["payload"]["data"]["AudioObjectCreateMutation"]["identifier"]
                        qry = trompace.queries.audioobject.query_audioobject(
                            identifier=identifier,
                            return_items=["contentUrl"]

                        )
                    else:
                        print("something wrong")

                    request_data = trompace.connection.submit_query(qry, auth_required=False)
                    contentUrl = request_data['data'][node_type][0]['contentUrl']
                    filename, file_extension = os.path.splitext(contentUrl)
                    file_extension = file_extension[1::]
                 #   extension = contentUrl((contentUrl.lastIndexOf(".") + 1):-1)

                    if file_extension in self.type_to_app[node_type]:
                        actions = self.type_to_app[node_type][file_extension]

                    for action in actions:
                        client = action['client']
                        storage = action['storage_file']
                        params = action['params']
                        qry = client.send_request([identifier], params, storage, execute=False)
                        print(qry)
                      #  action.e
                       # print(formatted)
                    print("ok")
               #     control_id = messageString["payload"]["data"]["ControlActionRequest"]["identifier"]
               #     qry = trompace.queries.controlaction.query_controlaction(control_id)
               #     request_data = trompace.connection.submit_query(qry, auth_required=False)
               #     print(request_data)
                #    params = tpl.tools.get_ca_params(request_data)

                if not is_ok:
                    raise Exception("don't have an ack yet")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trompa Processing Library Triggering')
    parser.add_argument('--trigger_ini', type=str, help='trigger config file', required=True)
    parser.add_argument('--ce_config', type=str, help='ce config file', required=True)

    args = parser.parse_args()

    trigger = Triggerer(args.trigger_ini, args.ce_config)
  #  trigger.batch("MediaObject")

 #   trigger.run()
    asyncio.run(trigger.run("MediaObject"))
    asyncio.run(trigger.run("AudioObject"))

    trigger = tpl.trigger.Triggerer(args.trigger_ini, args.ce_config)
    loop = asyncio.get_event_loop()
    task1 = loop.create_task(trigger.run("MediaObject"))
    task2 = loop.create_task(trigger.run("AudioObject"))

    loop.run_forever()