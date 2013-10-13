# minimal python class
class Parent:

    def __init__(self):
        self.message = 'héllo world'

    def say(self):
        print self.message



class Child(Parent):

    def __init__(self):
        Parent.__init__(self)
        self.more = 'how are you?'

    def greeting(self):
        print self.more


c = Child()
c.say()
c.greeting()
