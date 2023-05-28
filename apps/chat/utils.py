import uuid

def generate_umid():
    return str(uuid.uuid4().hex)[:24]