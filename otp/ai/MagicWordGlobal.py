from direct.showbase import PythonUtil

MINIMUM_MAGICWORD_ACCESS = 300

class MagicError(Exception): pass

def ensureAccess(access, msg='Insufficient access'):
    if spellbook.getInvokerAccess() < access:
        raise MagicError(msg)

class Spellbook:
    """
    The Spellbook manages the list of all Magic Words that have been registered
    anywhere in the system. When the MagicWordManager(AI) wants to process a
    Magic Word, it is passed off to the Spellbook, which performs the operation.

    To add Magic Words to the Spellbook, use the @magicWord() decorator.
    """

    def __init__(self):
        self.words = {}
        self.categories = []

        self.currentInvoker = None
        self.currentTarget = None

    def addWord(self, word):
        self.words[word.name] = word

    def addCategory(self, category):
        self.categories.append(category)

    def process(self, invoker, target, incantation):
        self.currentInvoker = invoker
        self.currentTarget = target
        word, args = (incantation.split(' ', 1) + [''])[:2]

        try:
            return self.doWord(word, args)
        except MagicError as e:
            return e.message
        except Exception:
            return PythonUtil.describeException(backTrace=1)
        finally:
            self.currentInvoker = None
            self.currentTarget = None

    def doWord(self, wordName, args):
        word = self.words.get(wordName)
        if not word:
            return

        ensureAccess(word.access)
        if self.getTarget() and self.getTarget() != self.getInvoker():
            if self.getInvokerAccess() <= self.getTarget().getAdminAccess():
                raise MagicError('Target must have lower access')

        result = word.run(args)
        if result is not None:
            return str(result)

    def getInvoker(self):
        return self.currentInvoker

    def getTarget(self):
        return self.currentTarget

    def getInvokerAccess(self):
        if not self.currentInvoker:
            return 0
        return self.currentInvoker.getAdminAccess()

spellbook = Spellbook()


# CATEGORIES
class MagicWordCategory:
    def __init__(self, name, defaultAccess=500, doc=''):
        self.name = name
        self.defaultAccess = defaultAccess
        self.doc = doc

        self.words = []

        spellbook.addCategory(self)

    def addWord(self, word):
        self.words.append(word)

CATEGORY_UNKNOWN = MagicWordCategory('Unknown')
CATEGORY_GRAPHICAL = MagicWordCategory('Graphical debugging', defaultAccess=300,
    doc='Magic Words in this category are used to assist developers in locating '
        'the cause of graphical glitches.')
CATEGORY_GUI = MagicWordCategory('GUI debugging', defaultAccess=300,
    doc='These Magic Words are intended to manipulate the on-screen GUI to '
        'assist developers in testing/debugging the GUI system.')
CATEGORY_MOBILITY = MagicWordCategory('Mobility cheats', defaultAccess=300,
    doc='These Magic Words allow you to move around the area/world more easily, '
        'allow you to get to areas more quickly.')
CATEGORY_OVERRIDE = MagicWordCategory('Override cheats', defaultAccess=400,
    doc='These Magic Words let you override normal game logic.')
CATEGORY_CHARACTERSTATS = MagicWordCategory('Character-stats cheats', defaultAccess=400,
    doc='These Magic Words let you alter the stats (e.g. gags, laff) of Toons.')
CATEGORY_DEBUG = MagicWordCategory('Debug cheats', defaultAccess=300,
    doc='These are Magic Words that may be useful in debugging, but have an impact '
        'on the fairness of the game if you use them, therefore they are considered '
        'cheats.')
CATEGORY_MODERATION = MagicWordCategory('Moderation commands', defaultAccess=300,
    doc='These are Magic Words focused on allowing moderators to deal with '
        'unruly players.')
CATEGORY_CAMERA = MagicWordCategory('Camera controls', defaultAccess=300,
    doc='These Magic Words manually control the camera system, originally implemented '
        'with Doomsday.')


class MagicWord:
    def __init__(self, name, func, types, access, doc, category):
        self.name = name
        self.func = func
        self.types = types
        self.access = access
        self.doc = doc
        self.category = category

        category.addWord(self)

    def getUsage(self):
        maxArgs = self.func.func_code.co_argcount
        minArgs = maxArgs - (len(self.func.func_defaults) if self.func.func_defaults else 0)
        argnames = self.func.func_code.co_varnames[:maxArgs]

        usageArgs = []

        for x in xrange(minArgs):
            usageArgs.append(argnames[x])

        for x in xrange(minArgs, maxArgs):
            usageArgs.append('[%s]' % argnames[x])

        return ' '.join(usageArgs)

    def parseArgs(self, string):
        maxArgs = self.func.func_code.co_argcount
        minArgs = maxArgs - (len(self.func.func_defaults) if self.func.func_defaults else 0)

        args = string.split(None, maxArgs-1)[:maxArgs]
        if len(args) < minArgs:
            raise MagicError('Magic word %s requires at least %d arguments' % (self.name, minArgs))

        output = []
        for i, (type, arg) in enumerate(zip(self.types, args)):
            try:
                targ = type(arg)
            except (TypeError, ValueError):
                raise MagicError('Argument %d of magic word %s must be %s' % (i, self.name, type.__name__))

            output.append(targ)

        return output

    def run(self, rawArgs):
        args = self.parseArgs(rawArgs)
        return self.func(*args)


class MagicWordDecorator:
    """
    This class manages Magic Word decoration. It is aliased as magicWord, so that
    the @magicWord(...) construct instantiates this class and has the resulting
    object process the Magic Word's construction.
    """

    def __init__(self, name=None, types=[str], access=None, category=CATEGORY_UNKNOWN):
        self.name = name
        self.types = types
        self.category = category
        if access is not None:
            self.access = access
        else:
            self.access = self.category.defaultAccess

    def __call__(self, mw):
        # This is the actual decoration routine. We add the function 'mw' as a
        # Magic Word to the Spellbook, using the attributes specified at construction
        # time.

        name = self.name
        if name is None:
            name = mw.func_name

        word = MagicWord(name, mw, self.types, self.access, mw.__doc__, self.category)
        spellbook.addWord(word)

        return mw

magicWord = MagicWordDecorator
