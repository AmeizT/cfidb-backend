import random

def generate_random_color():
    def generate_hex():
        return random.randint(0, 255)

    return '#%02X%02X%02X' % (generate_hex(), generate_hex(), generate_hex())
