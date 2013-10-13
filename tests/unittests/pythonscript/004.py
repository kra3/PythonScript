def telekin(self):
    print self.name, 'is telekinesing'


def higher_level_power(class_name, parents, attrs):
    attrs.telekin = telekin
    return type(class_name, parents, attrs)


class Person:

    __metaclass__ = higher_level_power

    def __init__(self, name):
        self.name = name

    def walk(self):
        print self.name, 'is walking'


aria = Person('aria')
aria.walk()
aria.telekin()
