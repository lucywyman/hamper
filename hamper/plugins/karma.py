import operator
import re
from collections import Counter, defaultdict
from datetime import datetime

from hamper.interfaces import ChatCommandPlugin, Command
from hamper.utils import ude, uen

from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.ext.declarative import declarative_base

SQLAlchemyBase = declarative_base()


class Karma(ChatCommandPlugin):
    '''Give, take, and scoreboard Internet Points'''

    """
    Hamper will look for lines that end in ++ or -- and modify that user's
    karma value accordingly

    NOTE: The user is just a string, this really could be anything...like
    potatoes or the infamous cookie clicker....
    """

    name = 'karma'

    priority = -2

    short_desc = 'karma - Give or take karma from someone'
    long_desc = ('username++ - Give karma\n'
                 'username-- - Take karma\n'
                 '!karma --top - Show the top 5 karma earners\n'
                 '!karma --bottom - Show the bottom 5 karma earners\n'
                 '!karma --giver - Show who\'s given the most positive karma\n'
                 '!karma --taker - Show who\'s given the most negative karma\n'
                 '!karma username - Show the user\'s karma count\n')

    gotta_catch_em_all = r"""# 3 or statement
                             (

                             # Starting with a (, look for anything within
                             # parens that end with 2 or more + or -
                             (?=\()[^\)]+\)(\+\++|--+) |

                             # Looking from the start of the line until 2 or
                             # more - or + are found. No whitespace in this
                             # grouping
                             ^[^\s]+(\+\++|--+) |

                             # Finally group any non-whitespace groupings
                             # that end with 2 or more + or -
                             [^\s]+?(\+\++|--+)((?=\s)|(?=$))
                            )
                          """

    regstr = re.compile(gotta_catch_em_all, re.X)

    def setup(self, loader):
        super(Karma, self).setup(loader)
        self.db = loader.db
        SQLAlchemyBase.metadata.create_all(self.db.engine)

    def message(self, bot, comm):
        """
        Check for strings ending with 2 or more '-' or '+'
        """
        super(Karma, self).message(bot, comm)

        # No directed karma giving or taking
        if not comm['directed'] and not comm['pm']:
            msg = comm['message'].strip().lower()
            # use the magic above
            words = self.regstr.findall(msg)
            # Do things to people
            karmas = self.modify_karma(words)
            # Notify the users they can't modify their own karma
            if comm['user'] in karmas.keys():
                bot.reply(comm, "Nice try, no modifying your own karma")
            # Commit karma changes to the db
            self.update_db(comm["user"], karmas)

    def modify_karma(self, words):
        """
        Given a regex object, look through the groups and modify karma
        as necessary
        """

        # 'user': karma
        k = defaultdict(int)

        if words:
            # For loop through all of the group members
            for word_tuple in words:
                word = word_tuple[0]
                ending = word[-1]
                # This will either end with a - or +, if it's a - subract 1
                # kara, if it ends with a +, add 1 karma
                change = -1 if ending == '-' else 1
                # Now strip the ++ or -- from the end
                if '-' in ending:
                    word = word.rstrip('-')
                elif '+' in ending:
                    word = word.rstrip('+')
                # Check if surrounded by parens, if so, remove them
                if word.startswith('(') and word.endswith(')'):
                    word = word[1:-1]
                # Finally strip whitespace
                word = word.strip()
                # Add the user to the dict
                if word:
                    k[word] += change
        return k

    def update_db(self, giver, receiverkarma):
        """
        Record a the giver of karma, the receiver of karma, and the karma
        amount. Typically the count will be 1, but it can be any positive or
        negative integer.
        """

        for receiver in receiverkarma:
            if receiver != giver:
                urow = KarmaTable(ude(giver), ude(receiver),
                                  receiverkarma[receiver])
                self.db.session.add(urow)
        self.db.session.commit()

    class KarmaList(Command):
        """
        Return the highest or lowest 5 receivers of karma
        """

        regex = r'^karma --(top|bottom)$'

        LIMIT = 5

        def command(self, bot, comm, groups):
            # We'll need all the rows
            kts = bot.factory.loader.db.session.query(KarmaTable).all()
            # From all the rows, tally the karma for each receiver
            receivers = defaultdict(int)
            for row in kts:
                receivers[row.receiver] += row.kcount
            rec_count = len(receivers.keys())
            rec_sorted = sorted(receivers.iteritems(),
                                key=operator.itemgetter(1))

            # We should limit the list of users to at most self.LIMIT
            limit = self.LIMIT if rec_count >= self.LIMIT else rec_count
            if limit:
                if groups[0] == 'top':
                    snippet = rec_sorted[-limit:]
                elif groups[0] == 'bottom':
                    snippet = rec_sorted[0:limit]
                else:
                    bot.reply(
                        comm, r'Something went wrong with karma\'s regex'
                    )
                    return

                for rec in snippet:
                    bot.reply(
                        comm, '%s\x0f: %d' % (uen(rec[0]), rec[1]),
                        encode=False
                    )
            else:
                bot.reply(comm, r'No one has any karma yet :-(')

    class UserKarma(Command):
        """
        Retrieve karma for a given user
        """

        # !karma <username>
        regex = r'^karma\s+([^-].*)$'

        def command(self, bot, comm, groups):
            # Play nice when the user isn't in the db
            kt = bot.factory.loader.db.session.query(KarmaTable)
            thing = ude(groups[0].strip().lower())
            rec_list = kt.filter(KarmaTable.receiver == thing).all()

            if rec_list:
                total = 0
                for r in rec_list:
                    total += r.kcount
                bot.reply(
                    comm, '%s has %d points' % (uen(thing), total),
                    encode=False
                )
            else:
                bot.reply(
                    comm, 'No karma for %s ' % uen(thing), encode=False
                )

    class KarmaGiver(Command):
        """
        Identifies the person who gives the most karma
        """

        regex = r'^karma --(giver|taker)$'

        def command(self, bot, comm, groups):
            kt = bot.factory.loader.db.session.query(KarmaTable)

            if groups[0] == 'giver':
                givers = Counter()
                positive_karma = kt.filter(KarmaTable.kcount > 0)
                for row in positive_karma:
                    givers[row.giver] += row.kcount

                m = givers.most_common(1)
                most = m[0] if m else None
                if most:
                    bot.reply(
                        comm,
                        '%s has given the most karma (%d)' %
                        (uen(most[0]), most[1])
                    )
                else:
                    bot.reply(
                        comm,
                        'No positive karma has been given yet :-('
                    )
            elif groups[0] == 'taker':
                takers = Counter()
                negative_karma = kt.filter(KarmaTable.kcount < 0)
                for row in negative_karma:
                    takers[row.giver] += row.kcount

                m = takers.most_common()
                most = m[-1] if m else None
                if most:
                    bot.reply(
                        comm,
                        '%s has given the most negative karma (%d)' %
                        (uen(most[0]), most[1])
                    )
                else:
                    bot.reply(
                        comm,
                        'No negative karma has been given yet'
                    )


class KarmaTable(SQLAlchemyBase):
    """
    Keep track of users karma in a persistant manner
    """

    __tablename__ = 'karma'

    # Calling the primary key user, though, really, this can be any string
    id = Column(Integer, primary_key=True)
    giver = Column(String)
    receiver = Column(String)
    kcount = Column(Integer)
    datetime = Column(DateTime, default=datetime.utcnow())

    def __init__(self, giver, receiver, kcount):
        self.giver = giver
        self.receiver = receiver
        self.kcount = kcount


karma = Karma()
