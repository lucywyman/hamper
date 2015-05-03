import random
import re
from datetime import datetime
from hamper.interfaces import ChatCommandPlugin, Command

from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base

SQLAlchemyBase = declarative_base()

class Name(ChatCommandPlugin):
	'''Random Name Generator: !name to generate a random name'''
	name = 'name'
    l1 = ["Pixelated ", "Linus ", "Mr.", "Doctor ", "Fernando ", 
            "Bacon ", "Mario ", "Professor ", "Velociraptor ", 
            "Baby monkey ", "Richard ", "Luigi ", "Peach ", 
            "Batman ", "Macafee ", "Mozilla ", "Luxe ", "Yoshi ",
            "Uzbekistan ", "Stanley ", "Stefon ", "Ayn ", "Hans ", 
            "Hipster ", "Cueball ", "YOLO ", "Hamper ", "Lady ", 
            "Randall ", "Stephen ", "HP ", "Stud " ]
    l2 = ["Octocat", "McGee", "Fiddlesticks", "Torvalds", 
            "Munroe", "Kitten", "Muffin", "Rasta Primavera", 
            "Fiddlesticks", "Dangerzone", "Jobs", "Stallman",
			"Moneybags", "Muffin", "Heisenberg", "Zaboomafoo", 
            "Honey", "Fox", "Hawking",
		    "Lovecraft", "Rand", "Vim", "the 34th"]
	priority = 0
    
    def setup(self, loader):
        super(Name, self).setup(loader)
        self.db = loader.db
        SQLAlchemyBase.metadata.create_all(self.db.engine)

        # Config
        config = loader.config.get("name", {})
        self.timezone = config.get('timezone', 'UTC')
        try:
            self.tzinfo = timezone(self.timezone)
        except UnknowTimeZoneError:
            self.tzinfo = timezone('UTC')
            self.timezone = 'UTC'

	class Name(Command):
		regex = r'^name$'
		name = 'name'
		def command(self, bot, comm, groups):
			name1 = random.choice(l1)
			name2 = random.choice(l2)
			bot.reply(comm, str(name1)+str(name2))

    class Addname(Command):
        regex = r'^addname$'
        name = 'addname'
        def command(self, bot, comm, groups):

