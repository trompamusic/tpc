import json
import cryptography.fernet

def get_sub_dict(query):
    payload = {"variables": {},
               "extensions": {},
               "query": query}
    message = {"id": "1",
               "type": "start",
               "payload": payload}
    return json.dumps(message)


def get_ca_params(ca_response):
    ret_val = dict()
    objects = ca_response['data']['ControlAction'][0]['object']
    for obj in objects:
        if obj['nodeValue'] is not None:
            ret_val[obj['name']] = obj['nodeValue']['source']
        elif obj['value'] is not None:
            ret_val[obj['name']] = obj['value']
        else:
            ret_val[obj['name']] = None

    return ret_val

def execute_command_line(command_line, requires_docker):
    print("hello world")

def encrypt_file(fn, key, out_fn):
    with open(fn, 'rb') as f:
        data = f.read()
    f.close()
    # this encrypts the data read from your json and stores it in 'encrypted'
    fernet = cryptography.fernet.Fernet(key)
    encrypted = fernet.encrypt(data)
    # this writes your new, encrypted data into a new JSON file
    with open(out_fn, 'wb') as f:
        f.write(encrypted)
    f.close()

def decrypt_file(fn, key, out_fn):
    with open(fn, 'rb') as f:
        data = f.read()
    f.close()

    # this encrypts the data read from your json and stores it in 'encrypted'
    fernet = cryptography.fernet.Fernet(key)
    decrypted = fernet.decrypt(data)
    # this writes your new, encrypted data into a new JSON file
    with open(out_fn, 'wb') as f:
        f.write(decrypted)
    f.close()

def generate_key(key_fn):
    key = cryptography.fernet.Fernet.generate_key()
    fp = open(key_fn, 'wb')
    fp.write(key)
    fp.close()

