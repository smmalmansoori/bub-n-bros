from __future__ import generators
import random, os, math
import gamesrv
import images
import boards
from boards import *
from images import ActiveSprite
from mnstrmap import GreenAndBlue, Bonuses, Diamonds, Stars, BigImages
from mnstrmap import PotionBonuses, Fire
from player import BubPlayer


EXTRA_BONUSES = ['StarBubble']  # ['Moebius']


questionmarklist = ['questionmark3',
                    'questionmark4',
                    'questionmark5',
                    'questionmark4',
                    'questionmark3',
                    'questionmark2',
                    'questionmark1',
                    'questionmark2']

class Bonus(ActiveSprite):
    bubblable = 1
    touchable = 1
    points = 750
    timeout = 250
    sound = 'Fruit'
    endaction = None
    multiply = 1

    def __init__(self, x, y, nimage=None, points=None, falling=1):
        if nimage is not None:
            self.nimage = nimage
        if points is not None:
            self.points = points
        ActiveSprite.__init__(self, images.sprget(self.nimage), x, y)
        self.taken_by = []
        self.gen.append(self.timeouter())
        if falling:
            self.gen.append(self.faller())

    def buildoutcome(self):
        return (self.__class__,)

    def faller(self):
        while self.y < boards.bheight:
            if onground_nobottom(self.x, self.y):
                yield None
                yield None
            else:
                self.move(self.x, (self.y+4) & ~3)
            yield None
        self.kill()

    def timeouter(self):
        for i in range(self.timeout):
            yield None
        if self.timeout:
            self.kill()

    def touched(self, dragon):
        if (dragon.x + dragon.ico.w > self.x + 10   and
            dragon.y + dragon.ico.h > self.y + 8    and
            self.x + self.ico.w     > dragon.x + 10 and
            self.y + self.ico.h     > dragon.y + 10):
            if not self.taken_by:
                self.gen = [self.taking()]
                sound = self.sound
                if sound:
                    if isinstance(sound, str):
                        sound = getattr(images.Snd, sound)
                    self.play(sound)
            if dragon not in self.taken_by:
                self.taken_by.append(dragon)
                if isinstance(self, (RandomBonus, MonsterBonus)):
                    s_bonus = dragon.bubber.stats.setdefault('bonus', {})
                    s_bonus[self.nimage] = s_bonus.get(self.nimage, 0) + 1

    def taking(self, follow_dragons=0, delay=1):
        from player import Dragon
        for t in range(delay):
            yield None   # time to be taken by several dragons
        if self.points:
            for p in self.taken_by:
                if follow_dragons and p.alive:
                    s = p
                else:
                    s = self
                points(s.x + s.ico.w//2, s.y + s.ico.h//2 - CELL, p, self.points)
        dragons = [d for d in self.taken_by if isinstance(d, Dragon)]
        if self.taken1(dragons) != -1:
            self.kill()

    def taken1(self, dragons):
        for d in dragons * self.multiply:
            if d.alive:
                self.taken(d)

    def taken(self, dragon):
        pass

    def in_bubble(self, bubble):
        self.untouchable()
        bubble.move(self.x, self.y)
        bubble.to_front()
        self.to_front()
        self.gen = [self.bubbling(bubble, self.ico)]
        self.move(bubble.x+8, bubble.y+8, images.sprget('questionmark3'))
        self.setimages(self.cyclic(questionmarklist, 2))

    def bubbling(self, bubble, ico):
        #dx = (bubble.ico.w - nico.w) // 2
        #dy = (bubble.ico.h - nico.h) // 2
        #dx = [dx, dx+1, dx, dx-1]
        #i = 0
        #while not hasattr(bubble, 'poplist'):
        #    self.move(bubble.x+dx[i//4], bubble.y+dy, nico)
        #    i = (i+1) % 16
        #    yield None
        while not hasattr(bubble, 'poplist'):
            self.move(bubble.x+8, bubble.y+8)
            yield None
        if bubble.poplist is not None:
            dragon = bubble.poplist[0]
            if dragon is not None:
                self.play(images.Snd.Yippee)
                if dragon not in self.taken_by:
                    self.taken_by.append(dragon)
                if self.points > 10:
                    dragon.bubber.givepoints(self.points - 10)
                    pn = dragon.bubber.pn
                    if self.points in GreenAndBlue.points[pn]:
                        Points(bubble.x + bubble.ico.w//2, bubble.y, pn, self.points)
                self.taken1(BubPlayer.DragonList)
                p = Parabolic(ico, bubble.x, bubble.y)
                p.gen.append(p.moving(-1.0))
        self.kill()


def points(x, y, dragon, points):
    dragon.bubber.givepoints(abs(points))
    pn = dragon.bubber.pn
    if points in GreenAndBlue.points[pn]:
        Points(x, y, pn, points)

class Points(ActiveSprite):

    def __init__(self, x, y, pn, points):
        ico = images.sprget(GreenAndBlue.points[pn][points])
        ActiveSprite.__init__(self, ico, x - ico.w//2, max(8, y))
        self.nooverlap = 1
        self.gen.append(self.raiser())

    def raiser(self):
        wait = 0
        for s in images.ActiveSprites:
            if s is self:
                break
            if (isinstance(s, Points) and s.nooverlap and
                abs(self.x-s.x)<self.ico.w*2//3 and
                abs(self.y-s.y)<self.ico.h):
                wait += 5
        for t in range(wait):
            yield None
        for i in range(25):
            if i == 7:
                self.nooverlap = 0
            self.step(0, -2)
            yield None
            if self.y <= 0:
                break
        for i in range(20):
            yield None
        self.kill()


class Parabolic(ActiveSprite):
    fallstraight = 0
    fallspeed = 4
    
    def moving(self, y_amplitude = -8.0):
        bottom_up = self.fallspeed < 0
        dxy = [(random.random()-0.5) * 15.0,
               (random.random()+0.5) * y_amplitude * (1,-1)[bottom_up]]
        if bottom_up:
            kw = {'gravity': -0.3}
        else:
            kw = {}
        for n in self.parabolic(dxy, self.fallstraight, **kw):
            yield n
            if dxy[1] * (1,-1)[bottom_up] >= 4.0 and self.fallstraight:
                self.gen.append(self.falling())
                return
        self.kill()

    def falling(self):
        nx = self.x
        ny = self.y & ~3
        if self.fallspeed < 0:
            groundtest = underground
        else:
            groundtest = onground
        while not groundtest(nx, ny):
            ny += self.fallspeed
            if ny < -2*CELL or ny >= boards.bheight:
                (nx, ny), moebius = boards.vertical_warp(nx, ny)
            self.move(nx, ny)
            yield None
        self.move(nx, ny)
        self.build()
        self.kill()

    def killmonsters(self, poplist):
        from monsters import Monster
        while 1:
            for s in self.touching(0):
                if isinstance(s, Monster):
                    s.argh(poplist)
            yield None

    def build(self):
        pass


class Parabolic2(Parabolic):
    points = 0

    def __init__(self, x, y, imglist, imgspeed=3, onplace=0, y_amplitude=-8.0):
        Parabolic.__init__(self, images.sprget(imglist[0]), x, y)
        if onplace:
            self.gen.append(self.falling())
        else:
            self.gen.append(self.moving(y_amplitude))
        if len(imglist) > 1:
            self.setimages(self.cyclic(imglist, imgspeed))

    def touched(self, dragon):
        if self.points:
            points(self.x + self.ico.w/2, self.y + self.ico.h/2 - CELL,
                   dragon, self.points)
            self.kill()


class BonusMaker(Parabolic2):
    fallstraight = 1
    touchable = 1

    def __init__(self, x, y, imglist, imgspeed=3, onplace=0, outcome=None):
        assert outcome
        self.outcome = outcome
        if outcome == (Flower2,):
            self.fallspeed = -self.fallspeed
        Parabolic2.__init__(self, x, y, imglist, imgspeed, onplace)

    def build(self):
        cls = self.outcome[0]
        args = self.outcome[1:]
        if issubclass(cls, RandomBonus) and not boards.curboard.playingboard:
            return None
        else:
            return cls(self.x, self.y, *args)

    def touched(self, dragon):
        pass


class MonsterBonus(Bonus):

    def __init__(self, x, y, multiple, forceimg=0):
        self.level = multiple
        if multiple >= len(Bonuses.monster_bonuses):
            multiple = len(Bonuses.monster_bonuses) - 1
        img, pts = Bonuses.monster_bonuses[multiple]
        Bonus.__init__(self, x, y, forceimg or img, pts)

    def buildoutcome(self):
        return (MonsterBonus, self.level)

    def taken(self, dragon):
        dragon.carrybonus(self, 543)


class RandomBonus(Bonus):
    timeout = 500

class TemporaryBonus(RandomBonus):
    captime = 0
    bonusleveldivider = 2
    def taken(self, dragon):
        dragon.dcap[self.capname] += 1
        self.carried(dragon)
    def carried(self, dragon):
        captime = self.captime
        if boards.curboard.bonuslevel:
            captime = (captime or 999) // self.bonusleveldivider
        if captime:
            dragon.carrybonus(self, captime)
        else:
            dragon.carrybonus(self)
            self.endaction = None
    def endaction(self, dragon):
        if dragon.dcap[self.capname] >= 1:
            dragon.dcap[self.capname] -= 1


class ShoeSpeed(RandomBonus):
    "Fast Runner. Cumulative increase of horizontal speed."
    nimage = Bonuses.shoe
    bigbonus = {'multiply': 3}
    def taken(self, dragon):
        dragon.dcap['hspeed'] += 1
        dragon.carrybonus(self)

class CoffeeSpeed(RandomBonus):
    "Caffeine. Cumulative increase of the horizontal speed and fire rate."
    nimage = Bonuses.coffee
    bigbonus = {'multiply': 3}
    def taken(self, dragon):
        dragon.dcap['hspeed'] += 0.5
        dragon.dcap['firerate'] += 1
        dragon.carrybonus(self)

class Butterfly(TemporaryBonus):
    "Lunar Gravity. Allows you to jump twice as high as before."
    nimage = Bonuses.butterfly
    bigbonus = {'multiply': 2}
    def taken(self, dragon):
        dragon.dcap['gravity'] *= 0.5
        self.carried(dragon)
    def endaction(self, dragon):
        dragon.dcap['gravity'] *= 2.0

class Cocktail(TemporaryBonus):
    "Short Lived Bubbles. Makes your bubbles explode more quickly."
    nimage = Bonuses.cocktail
    points = 2000
    capname = 'bubbledelay'

class Extend(RandomBonus):
    "E X T E N D. Gives you your missing letters and clear the level. "
    nimage = Bonuses.extend
    points = 0
    big = 0
    bigbonus = {'big': 1}

    def taken1(self, dragons):
        if self.big:
            self.letterexplosion()
        else:
            RandomBonus.taken1(self, dragons)
            
    def taken(self, dragon):
        from bubbles import extend_name
        names = [extend_name(l) for l in range(6)]
        missing = [name for name in names if name not in dragon.bubber.letters]
        x = dragon.x + dragon.ico.w//2
        y = dragon.y
        points(x, y, dragon, 10000*len(missing))
        for l in range(6):
            if extend_name(l) in missing:
                dragon.bubber.giveletter(l, promize=0)

    def letterexplosion(self):
        from bubbles import LetterBubble
        playercount = len([p for p in BubPlayer.PlayerList if p.isplaying()])
        N = 2 + (playercount > 3)
        angles = [i*(2.0*math.pi/N) for i in range(N)]
        for l, dx, dy in [(0,  5,  9), (1, 16, 10), (2, 26,  8),
                          (3,  7, 23), (4, 15, 24), (5, 25, 24)]:
            delta = 2.0*math.pi * random.random()
            angles = [angle-delta for angle in angles]
            x = self.x + self.ico.w//2 + 3*(dx-16)
            y = self.y + self.ico.h//2 + 3*(dy-16)
            for angle in angles:
                bubble = LetterBubble(None, l)
                bubble.thrown_bubble(x, y, 7.0 + 4.0 * random.random(),
                                     (math.cos(angle), math.sin(angle)))

class HeartPoison(RandomBonus):
    "Heart Poison. Freeze all free monsters."
    nimage = Bonuses.heart_poison
    big = 0
    bigbonus = {'big': 1}
    def taken1(self, dragons):
        import monsters
        monsters.freeze_em_all()
        if self.big:
            def heart_pause(dragon, gen):
                for i in range(222):
                    yield None
                dragon.gen = gen
            for d in BubPlayer.DragonList:
                if d not in dragons:
                    d.gen = [heart_pause(d, d.gen)]

class VioletNecklace(RandomBonus):
    "Monster Duplicator. Double the number of free monsters."
    points = 650
    nimage = Bonuses.violet_necklace
    bigbonus = {'multiply': 3}
    def taken1(self, dragons):
        for s in BubPlayer.MonsterList[:]:
            if s.regular():
                for i in range(self.multiply):
                    s.__class__(s.mdef, s.x, s.y, -s.dir * (-1)**i)

class WandBonus(RandomBonus):
    "Wand/Chest. Turn the bubble into bonuses at the end of the level."
    nimages = [Bonuses.brown_wand,   Bonuses.yellow_wand, Bonuses.green_wand,
               Bonuses.violet_wand,  Bonuses.blue_wand,   Bonuses.red_wand,
               Bonuses.violet_chest, Bonuses.blue_chest,  Bonuses.red_chest,
               Bonuses.yellow_chest,
               ]
    Modes = [
        (Bonuses.brown_wand,   750,  Bonuses.cyan_ice,    700,  BigImages.cyan_ice,    20000),
        (Bonuses.yellow_wand,  750,  Bonuses.violet_ice,  750,  BigImages.violet_ice,  20000),
        (Bonuses.green_wand,   750,  Bonuses.peach2,      800,  BigImages.peach2,      30000),
        (Bonuses.violet_wand,  750,  Bonuses.pastec2,     850,  BigImages.pastec2,     30000),
        (Bonuses.blue_wand,    750,  Bonuses.cream_pie,   900,  BigImages.cream_pie,   40000),
        (Bonuses.red_wand,     750,  Bonuses.sugar_pie,   950,  BigImages.sugar_pie,   40000),
        (Bonuses.violet_chest, 2000, Diamonds.violet,     6000, BigImages.violet,      60000),
        (Bonuses.blue_chest,   2000, Diamonds.blue,       7000, BigImages.blue,        60000),
        (Bonuses.red_chest,    2000, Diamonds.red,        8000, BigImages.red,         70000),
        (Bonuses.yellow_chest, 2000, Diamonds.yellow,     9000, BigImages.yellow,      70000),
        ]
    def __init__(self, x, y):
        self.mode = random.choice(WandBonus.Modes)
        RandomBonus.__init__(self, x, y, *self.mode[:2])
    def taken1(self, dragons):
        BubPlayer.BubblesBecome = self.bubble_outcome
        BubPlayer.MegaBonus     = self.mega_bonus
    def bubble_outcome(self, bubble):
        if bubble.pop():
            x = bubble.x
            if x < 2*CELL:
                x = 2*CELL
            elif x > boards.bwidth - 4*CELL:
                x = boards.bwidth - 4*CELL
            Bonus(x, bubble.y, *self.mode[2:4])
    def mega_bonus(self):
        nico, npoints = self.mode[4:6]
        ico = images.sprget(nico)
        x = random.randrange(0, boards.bwidth-ico.w)
        mb = Megabonus(x, -ico.h, nico, npoints)
        mb.outcome = (Bonus,) + self.mode[2:4]
        mb.outcome_image = self.mode[2]
WandBonus1 = WandBonus  # increase probability

class Megabonus(Bonus):
    touchable = 0
    vspeed = 6
    sound = 'Extra'
    coverwithbonus = 99
    
    def faller(self):
        self.fullpoints = self.points
        self.bubbles = {}
        for t in range(71):
            yield None
        self.ready_to_go()
        self.bubbles_pos = list(self.bubbles_position())
        self.gen.append(self.animate_bubbles())
        y0 = self.y - HALFCELL
        ymax = boards.bheight - CELL - self.ico.h
        self.touchable = 1
        ny = self.y
        while self.y >= y0:
            ny += self.vspeed
            if ny > ymax:
                ny = ymax
                self.vspeed = 0
            self.move(self.x, int(ny))
            yield None
        self.kill()

    def ready_to_go(self):
        pass

    def kill(self):
        for bubble in self.bubbles.values():
            bubble.pop()
        Bonus.kill(self)

    def taken(self, dragon):
        poplist = [dragon]
        for bubble in self.bubbles.values():
            bubble.pop(poplist)

    def bubbles_position(self):
        import time; start=time.time()
        cx = self.ico.w//2 - CELL
        cy = self.ico.h//2 - CELL
        positions = []
        pi2 = math.pi * 2
        dist = 10.0
        for i in range(31):
            while 1:
                angle = random.random() * pi2
                nx = cx + int(dist*math.sin(angle))
                ny = cy + int(dist*math.cos(angle))
                for ox, oy in positions:
                    if (nx-ox)*(nx-ox) + (ny-oy)*(ny-oy) < 220:
                        dist += 0.3
                        break
                else:
                    break
            positions.append((nx, ny))
        #print time.time()-start
        return positions
##        nx = 5
##        ny = 6
##        xmargin = 2
##        ymargin = 7
##        xstep = (self.ico.w+2*xmargin-2*CELL) / float(nx-1)
##        ystep = (self.ico.h+2*ymargin-2*CELL) / float(ny-1)
##        for dx in range(nx):
##            corner = dx in [0, nx-1]
##            for dy in range(corner, ny-corner):
##                dx1 = int(dx*xstep)-xmargin
##                dy1 = int(dy*ystep)-ymargin
##                yield (dx1 + random.randrange(-2,3),
##                       dy1 + random.randrange(-2,3))

    def nearest_free_point(self, x0, y0):
        distlst = [((x0-x)*(x0-x)+(y0-y)*(y0-y)+random.random(), x, y)
                   for x, y in self.bubbles_pos if (x, y) not in self.bubbles]
        if distlst:
            ignored, dx, dy = min(distlst)
            return dx, dy
        else:
            return None, None

    def in_bubble(self, bubble):
        dx, dy = self.nearest_free_point(bubble.x-self.x, bubble.y-self.y)
        if dx is not None:
            self.cover_bubble(dx, dy, bubble.d.bubber)
            self.gen.append(self.cover_bubbles(bubble.d.bubber))
        bubble.kill()

    def cover_bubbles(self, bubber):
        while 1:
            for t in range(2):
                yield None
            bubbles = [dxy for dxy, b in self.bubbles.items()
                           if b.bubber is bubber]
            if not bubbles:
                break
            dx, dy = self.nearest_free_point(*random.choice(bubbles))
            if dx is None:
                break
            self.cover_bubble(dx, dy, bubber)
        self.untouchable()

    def cover_bubble(self, dx, dy, bubber):
        if (dx, dy) in self.bubbles:
            return
        from bubbles import Bubble
        if len(self.bubbles) & 1:
            MegabonusBubble = Bubble
        elif self.coverwithbonus:
            self.coverwithbonus -= 1
            outcome = self.outcome
            outcome_image = self.outcome_image
            class MegabonusBubble(Bubble):
                def popped(self, dragon):
                    BonusMaker(self.x, self.y, [outcome_image], outcome=outcome)
                    return 10
        else:
            MegabonusBubble = Bubble
        
        nimages = GreenAndBlue.normal_bubbles[bubber.pn]
        b = MegabonusBubble(images.sprget(nimages[1]), self.x+dx, self.y+dy)
        b.dx = dx
        b.dy = dy
        b.bubber = bubber
        b.nimages = nimages
        self.bubbles[dx, dy] = b
        self.timeout = 0
        f = float(len(self.bubbles)) / len(self.bubbles_pos)
        self.vspeed = -0.73*f + self.vspeed*(1.0-f)
        self.points = int(self.fullpoints*(1.0-f) / 10000.0 + 0.9999) * 10000

    def animate_bubbles(self):
        if 0:  # disabled clipping
            d = {}
            for dx, dy in self.bubbles_pos:
                d[dx] = d[dy] = None
            north = d.copy()
            south = d.copy()
            west = d.copy()
            east = d.copy()
            del d
            for dx, dy in self.bubbles_pos:
                lst = [y for x, y in self.bubbles_pos if x==dx and y<dy]
                if lst: north[dy] = max(lst)
                lst = [y for x, y in self.bubbles_pos if x==dx and y>dy]
                if lst: south[dy] = min(lst)
                lst = [x for x, y in self.bubbles_pos if x<dx and y==dy]
                if lst: west[dx] = max(lst)
                lst = [x for x, y in self.bubbles_pos if x>dx and y==dy]
                if lst: east[dx] = min(lst)
            W = 2*CELL
            H = 2*CELL
        bubbles = self.bubbles
        while 1:
            for cycle in [1]*8 + [2]*10 + [1]*8 + [0]*10:
                yield None
                for (dx, dy), bubble in bubbles.items():
                    if not hasattr(bubble, 'poplist'):
                        if 0:   # disabled clipping
                            if (dx, north[dy]) in bubbles:
                                margin_n = (north[dy]+H-dy)//2
                            else:
                                margin_n = 0
                            if (dx, south[dy]) in bubbles:
                                margin_s = (dy+H-south[dy])//2
                            else:
                                margin_s = 0
                            if (west[dx], dy) in bubbles:
                                margin_w = (west[dx]+W-dx)//2
                            else:
                                margin_w = 0
                            if (east[dx], dy) in bubbles:
                                margin_e = (dx+W-east[dx])//2
                            else:
                                margin_e = 0
                            r = (margin_w,
                                 margin_n,
                                 W-margin_w-margin_e,
                                 H-margin_n-margin_s)
                            bubble.move(self.x + bubble.dx + margin_w,
                                        self.y + bubble.dy + margin_n,
                                        images.sprget_subrect(
                                            bubble.nimages[cycle], r))
                        else:
                            bubble.move(self.x + bubble.dx,
                                        self.y + bubble.dy,
                                        images.sprget(bubble.nimages[cycle]))
                    elif len(bubbles) == len(self.bubbles_pos):
                        self.pop_bubbles(bubble.poplist)
                        return

    def pop_bubbles(self, poplist):
        def bubble_timeout(bubble, vspeed):
            ny = bubble.y
            for t in range(random.randrange(15,25)):
                if hasattr(bubble, 'poplist'):
                    return
                ny += vspeed
                bubble.move(bubble.x, int(ny))
                yield None
            bubble.pop(poplist)

        for bubble in self.bubbles.values():
            bubble.gen.append(bubble_timeout(bubble, self.vspeed))
        self.bubbles.clear()
        self.kill()

class Cactus(RandomBonus):
    "Cactus. Drop a big version of a random bonus."
    points = 600
    nimage = 'cactus'
    extra_cheat_arg = None
    bigbonus = {'multiply': 3}
    
    def taken1(self, dragons):
        count = 0
        while count < self.multiply:
            if self.extra_cheat_arg:
                cls = globals()[self.extra_cheat_arg]
                self.extra_cheat_arg = None
            else:
                cls = random.choice(Classes)
            if makecactusbonus(cls):
                count += 1
        cactusbonussound()

Cactus1 = Cactus # increase probability

def makecactusbonus(cls, *args):
    bonus = cls(-3*CELL, 0, *args)
    if not bonus.alive or getattr(bonus, 'bigbonus', None) is None:
        return None
    bonus.__dict__.update(bonus.bigbonus)
    bonus.untouchable()
    bonus.gen = []
    mb = Cactusbonus(0, -3*CELL, 'cactus', 10000) # temp image
    mb.outcome = (cls,) + args
    mb.outcome_image = bonus.nimage
    mb.bonus = bonus
    mb.gen.append(mb.prepare_image())
    return mb

def cactusbonussound():
    gamesrv.set_musics([], [])
    boards.curboard.set_musics(prefix=[images.music_modern])

class Cactusbonus(Megabonus):
    coverwithbonus = 5

    def prepare_image(self):
        while images.computebiggericon(self.bonus.ico) is None:
            yield None

    def ready_to_go(self):
        ico = images.biggericon(self.bonus.ico)
        x = random.randrange(0, boards.bwidth-ico.w)
        self.move(x, -ico.h, ico)

    def taken1(self, dragons):
        d1 = list(dragons)
        Megabonus.taken1(self, dragons)
        if self.bonus.alive:
            x = self.x + self.ico.w//2 - CELL
            y = self.y + self.ico.h//2 - CELL
            self.bonus.move(x, y)
            self.bonus.taken1(d1)
            self.bonus.kill()

def starexplosion(x, y, multiplyer, killmonsters=0, outcomes=[]):
    outcomes = list(outcomes)
    poplist = [None]
    for i in range(multiplyer):
        items = Stars.__dict__.items()
        random.shuffle(items)
        for key, value in items:
            if not key.startswith('_'):
                if outcomes:
                    BonusMaker(x, y, value, outcome=outcomes.pop())
                else:
                    b = Parabolic2(x, y, value)
                    if killmonsters:
                        b.gen.append(b.killmonsters(poplist))

class Book(RandomBonus):
    "Magic Bomb. Makes a magical explosion killing touched monsters."
    points = 2000
    nimage = Bonuses.book
    bigbonus = {'multiply': 4}
    def taken1(self, dragons):
        starexplosion(self.x, self.y, self.multiply, killmonsters=1)

class Potion(RandomBonus):
    "Potions. Clear the level and fill its top with bonuses."
    nimages = [Bonuses.red_potion, Bonuses.green_potion, Bonuses.yellow_potion,
               'potion4']
    Potions = [(Bonuses.red_potion,    150,  [(PotionBonuses.coin,        350),
                                              (PotionBonuses.rainbow,     600)]),
               (Bonuses.green_potion,  350,  [(PotionBonuses.flower,     1000),
                                              (PotionBonuses.trefle,     2000)]),
               (Bonuses.yellow_potion, 550,  [(PotionBonuses.green_note, 2000),
                                              (PotionBonuses.blue_note,  3000)]),
               ('potion4',             750,  None),
               ]
    LocalDir = os.path.dirname(__file__) or os.curdir
    Extensions = [s for s in os.listdir(LocalDir)
                    if s.startswith('ext') and
                       os.path.isdir(os.path.join(LocalDir, s))]
    random.shuffle(Extensions)
    extra_cheat_arg = None
    big = 0

    def __init__(self, x, y):
        p_normal = 3
        if boards.curboard.bonuslevel:
            p_extension = 2       # make extensions rare in the bonus level
        else:
            p_extension = 5
        if self.extra_cheat_arg:
            Potion.Extensions.append(self.extra_cheat_arg)
            p_normal = 0
        if not Potion.Extensions:
            p_extension = 0
        choices = []
        for mode in Potion.Potions:
            if mode[2] is None:
                p = p_extension
            else:
                p = p_normal
            choices += [mode] * p
        self.mode = random.choice(choices)
        if self.mode[2] is not None:
            self.bigbonus = {'big': 1}
        RandomBonus.__init__(self, x, y, *self.mode[:2])
    def taken1(self, dragons):
        blist = self.mode[2]
        if blist is not None:
            if random.random() < 0.6:
                blist = [random.choice(blist)]
            boards.replace_boardgen(boards.potion_fill(blist, self.big))
        elif Potion.Extensions:
            ext = Potion.Extensions.pop()
            ext = __import__(ext, globals(), locals(), ['run'])
            ext.run()
            boards.BoardGen.append(boards.extra_bkgnd_black(self.x, self.y))

class FireBubble(RandomBonus):
    "Fire Bubbles. Makes you fire napalm bubbles."
    nimage = Bonuses.hamburger
    bubkind = 'FireBubble'
    bubcount = 10
    bigbonus = {'bubkind': 'BombBubble'}
    def taken(self, dragon):
        dragon.dcap['shootbubbles'] = [self.bubkind] * self.bubcount
        dragon.carrybonus(self)

class WaterBubble(FireBubble):
    "Water Bubbles. Your bubbles will now be filled with water."
    nimage = Bonuses.beer
    bubkind = 'WaterBubble'
    bigbonus = {'bubkind': 'SolidBubble'}

class LightningBubble(FireBubble):
    "Lightning Bubbles."
    nimage = Bonuses.french_fries
    bubkind = 'LightningBubble'
    bigbonus = {'bubkind': 'BigLightBubble'}

class Door(RandomBonus):
    "Magic Door. Let bonuses come in!"
    points = 1000
    nimage = Bonuses.door
    bigbonus = {'multiply': 3}
    def taken1(self, dragons):
        for img in [0, Diamonds.blue, Diamonds.violet][:self.multiply]:
            starexplosion(self.x, self.y, 2,
                          outcomes = [(MonsterBonus, -1, img)] * 10)

class LongFire(RandomBonus):
    "Long Fire. Increase the range of your bubble throw out."
    nimage = Bonuses.softice1
    big = 0
    bigbonus = {'big': 1}
    def taken(self, dragon):
        if self.big:
            dragon.dcap['flower'] = 0   # triple fire
        else:
            dragon.dcap['shootthrust'] *= 1.5
        dragon.carrybonus(self)

class ShortFire(RandomBonus):
    "Short Fire. Shorten the range of your bubble throw out."
    nimage = Bonuses.softice2
    points = 300
    factor = 1 / 1.5
    bigbonus = {'factor': 0}
    def taken(self, dragon):
        dragon.dcap['shootthrust'] *= self.factor
        dragon.carrybonus(self)

class HighSpeedFire(RandomBonus):
    "High Speed Fire. Increase your fire rate."
    nimage = Bonuses.custard_pie
    points = 700
    bigbonus = {'multiply': 4}
    def taken(self, dragon):
        dragon.dcap['firerate'] += 1.5
        dragon.carrybonus(self)

class Mushroom(TemporaryBonus):
    "Bouncy Bouncy. Makes you jump continuously."
    nimage = Bonuses.mushroom
    points = 900
    capname = 'pinball'
    captime = 625
    bigbonus = {'captime': captime*2, 'multiply': 2}

class Glue(TemporaryBonus):
    "Glue. Keep your feet on the ground."
    nimage = 'glue'
    points = 850
    capname = 'nojump'
    captime = 635

class AutoFire(TemporaryBonus):
    "Auto Fire. Makes you fire continuously."
    nimage = Bonuses.rape
    points = 800
    capname = 'autofire'
    captime = 675

class Insect(RandomBonus):
    "Crush World."
    nimage = Bonuses.insect
    big = 0
    bigbonus = {'big': 1}
    def taken1(self, dragons):
        boards.extra_boardgen(boards.extra_walls_falling(self.big))

class Ring(TemporaryBonus):
    "The One Ring."
    nimage = Bonuses.ring
    points = 4000
    capname = 'ring'
    captime = 700
    bonusleveldivider = 5
    bigbonus = {'multiply': 3}

class GreenPepper(TemporaryBonus):
    "Hot Pepper. Run! Run! That burns."
    nimage = Bonuses.green_pepper
    capname = 'hotstuff'
    captime = 100
    bigbonus = {'captime': captime*2}

class Lollipop(TemporaryBonus):
    "Yo Man! Makes you walk backward."
    nimage = Bonuses.lollipop
    def taken(self, dragon):
        dragon.dcap['left2right'] = -dragon.dcap['left2right']
        self.carried(dragon)
    def endaction(self, dragon):
        dragon.dcap['left2right'] = -dragon.dcap['left2right']

class Chickpea(TemporaryBonus):
    "Basilik. Allows you to touch the monsters."
    nimage = Bonuses.chickpea
    points = 800
    capname = 'overlayglasses'
    captime = 230
    #bigbonus = {'multiply': 2, 'captime': 240 + captime}
    def taken(self, dragon):
        TemporaryBonus.taken(self, dragon)
        dragon.dcap['shield'] += 250

class IceCream(RandomBonus):
    "Icecream. An icecream which is so good you'll always want more."
    nimages = [Bonuses.icecream6, Bonuses.icecream5,
               Bonuses.icecream4, Bonuses.icecream3]
    IceCreams = [(Bonuses.icecream6,  250),
                 (Bonuses.icecream5,  500),
                 (Bonuses.icecream4,  1000),
                 (Bonuses.icecream3,  2000)]
    big = 0
    bigbonus = {'big': 1}
    def __init__(self, x, y, generation=0):
        self.generation = generation
        RandomBonus.__init__(self, x, y, *self.IceCreams[generation])
    def taken1(self, dragons):
        nextgen = self.generation + 1
        if nextgen < len(self.IceCreams):
            for i in range(2):
                if self.big:
                    makecactusbonus(IceCream, nextgen)
                else:
                    x, y = chooseground(200)
                    if x is None:
                        return
                    IceCream(x, y, nextgen)
            if self.big:
                cactusbonussound()

class Grenade(RandomBonus):
    "Barbecue."
    nimage = Bonuses.grenade
    points = 550
    big = 0
    bigbonus = {'big': 1}
    def taken1(self, dragons):
        from bubbles import FireFlame
        poplist = [None]
        for y in range(1, boards.height-1):
            for x in range(2, boards.width-2):
                if bget(x,y) != ' ':
                    continue
                if bget(x,y+1) == '#':
                    FireFlame(x, y, poplist)
                elif self.big:
                    if bget(x,y-1) == '#':
                        FireFlame(x, y, poplist, flip='vflip')
                    elif bget(x-1,y) == '#':
                        FireFlame(x, y, poplist, flip='cw')
                    elif bget(x+1,y) == '#':
                        FireFlame(x, y, poplist, flip='ccw')

class Conch(RandomBonus):
    "Sea Shell. Let's bring the sea here!"
    nimage = Bonuses.conch
    points = 650
    def taken1(self, dragons):
        boards.extra_boardgen(boards.extra_water_flood())

##class Umbrella(RandomBonus):
##    Umbrellas = [(Bonuses.brown_umbrella,  2),
##                 (Bonuses.grey_umbrella,   3),
##                 (Bonuses.violet_umbrella, 4)]
##    points = 0
##    def __init__(self, x, y):
##        self.mode = random.choice(Umbrella.Umbrellas)
##        RandomBonus.__init__(self, x, y, self.mode[0])
##    def taken1(self, dragons):
##        boards.replace_boardgen(boards.umbrella(self, self.mode[1]))
##        return -1

def fire_rain(x, poplist):
    from bubbles import FireDrop
    FireDrop(x, -CELL, poplist)

def water_rain(x, poplist):
    from bubbles import watercell
    watercell(x, 0, poplist)

def ball_rain(x, poplist):
    from bubbles import SpinningBall
    SpinningBall(x, -CELL, poplist)

class Umbrella(RandomBonus):
    "Umbrellas. Beware of what's going to fall on everyone's head!"
    nimages = [Bonuses.brown_umbrella, Bonuses.grey_umbrella,
               Bonuses.violet_umbrella]
    Umbrellas = [(Bonuses.brown_umbrella,  900,  fire_rain,  10, 60),
                 (Bonuses.grey_umbrella,   950,  water_rain, 5,  60),
                 (Bonuses.violet_umbrella, 1000, ball_rain,  9, 120)]
    bigbonus = {'multiply': 3.1416}
    def __init__(self, x, y):
        self.mode = random.choice(Umbrella.Umbrellas)
        RandomBonus.__init__(self, x, y, *self.mode[:2])
    def taken1(self, dragons):
        for i in range(self.multiply):
            boards.extra_boardgen(self.raining())
    def raining(self):
        builder, drops, timemax = self.mode[2:]
        timemax = int(timemax * math.sqrt(self.multiply))
        drops = int(drops * self.multiply)
        times = [random.randrange(0, timemax) for i in range(drops)]
        poplist = [None]
        for t in range(timemax):
            for i in range(times.count(t)):
                x = random.randrange(2*CELL, bwidth-3*CELL+1)
                builder(x, poplist)
            yield 0

class Fruits(RandomBonus):
    "Fruits. A small little bonus. But the size doesn't matter, does it? If you're lucky enough you might get a great shower!"
    nimages = [Bonuses.kirsh, Bonuses.erdbeer, Bonuses.tomato,
               Bonuses.apple, Bonuses.corn, Bonuses.radish]
    bubblable = 0
    sound = 'Extra'
    Fruits = [(Bonuses.kirsh,      100),
              #(Bonuses.icecream1,  150),
              (Bonuses.erdbeer,    150),
              #(Bonuses.fish1,      250),
              (Bonuses.tomato,     200),
              #(Bonuses.donut,      250),
              (Bonuses.apple,      250),
              (Bonuses.corn,       300),
              #(Bonuses.icecream2,  600),
              (Bonuses.radish,     350),
              ]
    def __init__(self, x, y):  # x and y ignored !
        fine = 0
        for i in range(20):
            x0 = random.randint(3, boards.width-5)
            y0 = random.randint(1, boards.height-3)
            for xt in range(x0-1, x0+3):
                if xt == x0-1 or xt == x0+2:
                    yplus = 1
                else:
                    yplus = 0
                for yt in range(y0+yplus, y0+4-yplus):
                    if bget(xt,yt) != ' ':
                        break
                else:
                    continue
                break
            else:
                x, y = x0*CELL, y0*CELL
                fine = 1
                break
        mode = random.choice(Fruits.Fruits)
        RandomBonus.__init__(self, x, y, falling=0, *mode)
        self.repeatcount = 0
        if not fine:
            self.kill()
        elif random.random() < 0.04:
            self.superfruit = mode
            self.sound = 'Shh'
            self.points = 0
            self.repeatcount = random.randrange(50,100)
    def taken1(self, dragons):
        if self.repeatcount:
            image, points = self.superfruit
            f = Parabolic2(self.x, self.y, [image], y_amplitude = -1.5)
            f.points = points
            f.touchable = 1
            self.repeatcount -= 1
            self.gen.append(self.taking(1, 2))
            return -1
Fruits1 = Fruits  # increase probability
Fruits2 = Fruits
Fruits3 = Fruits
Fruits4 = Fruits
Fruits5 = Fruits
Fruits6 = Fruits

class BlueNecklace(RandomBonus):
    "Self Duplicator. Mirror yourself."
    points = 1000
    nimage = Bonuses.blue_necklace
    big = 0
    bigbonus = {'big': 1}
    def taken(self, dragon):
        if len(dragon.bubber.dragons) >= 7:
            # avoid burning the server with two much dragons
            return
        if self.big:
            from bubbles import Bubble
            ico = images.sprget(GreenAndBlue.normal_bubbles[dragon.bubber.pn][0])
            for sign in [-1, 1, -1]:
                d = self.makecopy(dragon, sign)
                b = Bubble(ico, d.x, d.y)
                d.become_bubblingeyes(b)
        else:
            d1 = random.choice([dragon, self.makecopy(dragon)])
            d1.carrybonus(self, 250)

    def makecopy(self, dragon, sign=-1):
        from player import Dragon
        d = Dragon(dragon.bubber, dragon.x, dragon.y, -dragon.dir, dragon.dcap)
        d.dcap['left2right'] = sign * d.dcap['left2right']
        d.up = dragon.up
        s = (dragon.dcap['shield'] + 12) & ~3
        dragon.dcap['shield'] = s+2
        d.dcap['shield'] = s
        dragon.bubber.dragons.append(d)
        return d

class Monsterer(RandomBonus):
    "Monsterificator. Let's play on the other side!"
    nimages = [Bonuses.red_crux, Bonuses.blue_crux]
    Sizes = [(Bonuses.red_crux, 800), (Bonuses.blue_crux, 850)]
    mlist = [['Nasty',  'Monky',  'Springy', 'Orcy'],
             ['Ghosty', 'Flappy', 'Gramy',   'Blitzy']
             ]
    big = 0
    bigbonus = {'big': 1}
    def __init__(self, x, y):
        self.mode = random.choice([0,1])
        RandomBonus.__init__(self, x, y, *self.Sizes[self.mode])
    def taken(self, dragon):
        mcls = random.choice(self.mlist[self.mode])
        dragon.become_monster(mcls, self.big)

Monsterer1 = Monsterer # increase probability

class Bubblizer(RandomBonus):
    "Bubblizer."
    points = 750
    nimage = Bonuses.gold_crux
    big = 0
    bigbonus = {'big': 1}
    def taken(self, dragon):
        if self.big:
            from bubbles import BombBubble, BigLightBubble
            bcls = random.choice([BombBubble, BigLightBubble])
        else:
            from bubbles import FireBubble, WaterBubble, LightningBubble
            bcls = random.choice([FireBubble, WaterBubble, LightningBubble])
        b = bcls(dragon.bubber.pn)
        b.move(dragon.x, dragon.y)
        if not dragon.become_bubblingeyes(b):
            b.kill()

class Carrot(RandomBonus):
    "Angry Monster. Turns all free monsters angry."
    nimage = Bonuses.carrot
    points = 950
    ghost = 0
    bigbonus = {'ghost': 1}
    def taken1(self, dragons):
        from monsters import Monster
        lst = [s for s in images.ActiveSprites
               if isinstance(s, Monster) and s.regular()]
        if lst:
            if self.ghost:
                images.Snd.Hell.play()
                for s in lst:
                    s.become_ghost()
            else:
                for s in lst:
                    s.angry = [s.genangry()]
                    s.resetimages()

class Egg(RandomBonus):
    "Teleporter. Exchange yourself with somebody else."
    nimage = Bonuses.egg
    def taken1(self, dragons):
        dragons = [d for d in dragons if d in d.bubber.dragons]
        alldragons = [d for d in BubPlayer.DragonList if d in d.bubber.dragons]
        others = [d for d in alldragons if d not in dragons]
        xchg = {}
        random.shuffle(dragons)
        random.shuffle(others)
        while dragons and others:
            d1 = dragons.pop()
            d2 = others.pop()
            xchg[d1] = d2.bubber
            xchg[d2] = d1.bubber
        if len(dragons) > 1:
            copy = dragons[:]
            for i in range(10):
                random.shuffle(copy)
                for j in range(len(dragons)):
                    if dragons[j] == copy[j]:
                        break
                else:
                    break
            for d1, d2 in zip(dragons, copy):
                xchg[d1] = d2.bubber
        elif len(dragons) == 1:
            x, y = chooseground(200)
            if x is not None:
                d1 = dragons[0]
                d1.move(x, y)
                d1.dcap['shield'] = 50
        for d1, bubber2 in xchg.items():
            d1.bubber.dragons.remove(d1)
            d1.bubber = bubber2
            bubber2.dragons.append(d1)
            d1.dcap['shield'] = 50

class Bomb(RandomBonus):
    "Baaoouuuummmm! Explode that wall!"
    nimage = Bonuses.bomb
    bigbonus = {'multiply': 3.8}
    def taken1(self, dragons):
        bomb_explosion(self.x, self.y, self.multiply)

def bomb_explosion(x0, y0, multiply=1, starmul=2):
    RADIUS = 3.9 * CELL * math.sqrt(multiply)
    Radius2 = RADIUS * RADIUS
    brd = boards.curboard
    cx = x0 + HALFCELL
    cy = y0 + HALFCELL - RADIUS/2
    for y in range(0, brd.height):
        dy1 = abs(y*CELL - cy)
        dy2 = abs((y-(brd.height-1))*CELL - cy)
        dy3 = abs((y+(brd.height-1))*CELL - cy)
        dy = min(dy1, dy2, dy3)
        for x in range(2, brd.width-2):
            dx = x*CELL - cx
            if dx*dx + dy*dy < Radius2:
                try:
                    brd.killwall(x,y)
                except KeyError:
                    pass
    brd.reorder_walls()
    starexplosion(x0, y0, starmul)
    gen = boards.extra_display_repulse(x0+CELL, y0+CELL,
                                       15000 * multiply,
                                       1000 * multiply)
    boards.extra_boardgen(gen)

class Ham(RandomBonus):
    "Protein. Let's build something!"
    nimage = Bonuses.ham
    bigbonus = {'multiply': 3.4}
    def taken1(self, dragons):
        RADIUS = 3.9 * CELL * math.sqrt(self.multiply)
        Radius2 = RADIUS * RADIUS
        brd = boards.curboard
        cx = self.x + HALFCELL
        cy = self.y + HALFCELL - RADIUS/2
        xylist = []
        for y in range(0, brd.height):
            dy1 = abs(y*CELL - cy)
            dy2 = abs((y-(brd.height-1))*CELL - cy)
            dy3 = abs((y+(brd.height-1))*CELL - cy)
            dy = min(dy1, dy2, dy3)
            for x in range(2, brd.width-2):
                dx = x*CELL - cx
                if dx*dx + dy*dy < Radius2:
                    if (y,x) not in brd.walls_by_pos and random.random() < 0.5:
                        brd.putwall(x,y)
                        xylist.append((x, y))
        brd.reorder_walls()
        boards.extra_boardgen(boards.single_blocks_falling(xylist))
        gen = boards.extra_display_repulse(self.x+CELL, self.y+CELL,
                                           5000 * self.multiply,
                                           1000 * self.multiply)
        boards.extra_boardgen(gen)

class Chestnut(RandomBonus):
    "Relativity. Speed up or slow down the game."
    nimage = Bonuses.chestnut
    sound = None
    dilatation = [0.5, 2.0]
    bigbonus = {'dilatation': [1/3.0, 3.0]}
    def taken1(self, dragons):
        m = self.multiply
        if m > 2:
            m = 2
        boards.set_frametime(random.choice(self.dilatation))
        BubPlayer.MultiplyerReset = BubPlayer.FrameCounter + 500
        self.play(images.Snd.Fruit)


try:
    import statesaver
except ImportError:
    print "'statesaver' module not compiled, no clock bonus"
else:
    import new
    def standard_build(self):
        return new.instance(self.__class__)
    boards.Copyable.inst_build = standard_build
    gamesrv.Sprite.inst_build = standard_build

    def copygamestate():
        # makes a copy of the game state.
        ps = []
        for p1 in BubPlayer.PlayerList:
            #if p1.isplaying():
            d = p1.__dict__.copy()
            for key in BubPlayer.TRANSIENT_DATA:
                if key in d:
                    del d[key]
            ps.append(d)
            #else:
            #    ps.append(None)
        topstate = (
            [g for g in boards.BoardGen if not g.gi_running],
            boards.curboard,
            images.ActiveSprites,
            images.SpritesByLoc,
            BubPlayer.__dict__,
            gamesrv.sprites,
            gamesrv.sprites_by_n,
            ps,
            images.Snd.__dict__,
            )
        #import pdb; pdb.set_trace()
        return statesaver.copy(topstate)

    def restoregamestate(savedstate):
        (boards.BoardGen,
         boards.curboard,
         images.ActiveSprites,
         images.SpritesByLoc,
         BubPlayer.__dict__,
         gamesrv.sprites,
         gamesrv.sprites_by_n,
         ps,
         images.Snd.__dict__,
         ) = savedstate

        for p, d in zip(BubPlayer.PlayerList, ps):
            #if d is None:
            #    p.reset()
            #else:
            p.__dict__.update(d)
            if not p.isplaying():
                p.zarkoff()

    class Clock(RandomBonus):
        "Time Machine. Let's do it again!"
        touchable = 0
        points = 0
        nimage = Bonuses.clock
        def __init__(self, x, y):
            RandomBonus.__init__(self, -boards.bwidth, 0)
            #print "starting clock"
            self.savedstate = None
            self.savedscreens = []
            self.gen = [self.delayed_show()]
            boards.extra_boardgen(self.state_saver())
        def delayed_show(self):
            for i in range(10):
                yield None
            if self.savedstate is not None:
                for i in range(55):
                    yield None
                x, y = chooseground(200)
                if x is not None:
                    self.move(x, y)
                    self.touchable = 1
                    self.gen.append(self.timeouter())
                    self.gen.append(self.faller())
                    return
            self.kill()
        def taken1(self, dragons):
            savedstate = self.savedstate
            self.savedstate = None
            if savedstate is not None:
                boards.replace_boardgen(self.state_restorer(savedstate,
                                                            self.savedscreens,
                                                            self))
                self.untouchable()
                return -1

        def state_saver(self):
            # called from BoardGen
            self.savedstate = copygamestate()
            while self.alive:
                gamesrv.sprites[0] = ''
                data = ''.join(gamesrv.sprites)
                self.savedscreens.append(data)
                yield 0
                yield 0
                self.savedscreens.append(data)
                yield 0
                yield 0
            self.savedscreens = []
        def state_restorer(self, savedstate, savedscreens, blinkme):
            # called from BoardGen
            from player import scoreboard
            status = 0
            for t in range(10):
                if not (t & 1):
                    gamesrv.sprites[0] = ''
                    savedscreens.append(''.join(gamesrv.sprites))
                time = boards.normal_frame()
                for i in range(t):
                    status += 1
                    if status % 3 == 0 and blinkme.alive:
                        if status % 6 == 0:
                            blinkme.step(boards.bwidth, 0)
                        else:
                            blinkme.step(-boards.bwidth, 0)
                    yield time
            yield boards.force_singlegen()
            yield 15.0
            for p1 in BubPlayer.PlayerList:
                del p1.dragons[:]
            delay = 8.5
            gamesrv.clearsprites()
            while savedscreens:
                gamesrv.sprites[:] = ['', savedscreens.pop()]
                if delay > 0.6:
                    delay *= 0.9
                yield delay
            yield 15.0
            restoregamestate(savedstate)
            scoreboard()
            yield 2.5

class MultiStones(RandomBonus):
    "Gems. Very demanded stones. It will take time to pick it up."
    nimages = [Bonuses.emerald, Bonuses.sapphire, Bonuses.ruby]
    Stones = [(Bonuses.emerald,    1000),
              (Bonuses.sapphire,   2000),
              (Bonuses.ruby,       3000),
              ]
    def __init__(self, x, y):
        mode = random.choice(MultiStones.Stones)
        RandomBonus.__init__(self, x, y, *mode)
        self.multi = 10
    def taken1(self, dragons):
        self.multi -= len(dragons)
        if self.multi > 0:
            self.taken_by = []
            self.untouchable()
            self.gen.append(self.touchdelay(5))
            return -1     # don't go away

class Slippy(TemporaryBonus):
    "Greased Feet. Do you want some ice skating?"
    nimage = Bonuses.orange_thing
    points = 900
    capname = 'slippy'
    captime = 606
    #bigbonus = {'captime': captime*2}

class Aubergine(TemporaryBonus):
    "Mirror. The left hand is the one with the thumb on the right, right?"
    nimage = Bonuses.aubergine
    #bigbonus = {'multiply': 3}
    def taken(self, dragon):
        dragon.dcap['lookforward'] = -dragon.dcap['lookforward']
        self.carried(dragon)
    def endaction(self, dragon):
        dragon.dcap['lookforward'] = -dragon.dcap['lookforward']

class WhiteCarrot(TemporaryBonus):
    "Fly. Become a great flying dragon!"
    nimage = Bonuses.white_carrot
    points = 650
    capname = 'fly'
    captime = 650
    bigbonus = {'multiply': 2}

class AmphetamineSpeed(TemporaryBonus):
    "Amphetamine Dose. Increase of your general speed!"
    nimage = Bonuses.tin
    points = 700
    bigbonus = {'multiply': 3}
    def taken(self, dragon):
        dragon.angry = dragon.angry + [dragon.genangry()]
        dragon.carrybonus(self, 633)
    def endaction(self, dragon):
        dragon.angry = dragon.angry[1:]

class Sugar1(Bonus):
    nimage = Bonuses.yellow_sugar
    timeout = 2600
    points = 250
    def taken(self, dragon):
        #if boards.curboard.wastingplay is None:
            dragon.carrybonus(self, 99999)
        #else:
        #    from player import scoreboard
        #    dragon.bubber.bonbons += 1
        #    scoreboard()

class Sugar2(Sugar1):
    timeout = 2500
    points = 500
    nimage = Bonuses.blue_sugar

class Pear(RandomBonus):
    "Pear. Will explode into sugars for your pockets but watch out or you'll lose them!"
    points = 1000
    nimage = Bonuses.green_thing
    bigbonus = {'multiply': 3}
    def taken1(self, dragons):
        starexplosion(self.x, self.y, 3 * self.multiply,
                      outcomes = [random.choice([(Sugar1,), (Sugar2,)])
                                  for i in range(18 * self.multiply)])

class Megalightning(ActiveSprite):
    def __init__(self, x1, y1, dragon):
        ActiveSprite.__init__(self, images.sprget(BigImages.blitz),
                              gamesrv.game.width, gamesrv.game.height)
        self.gen.append(self.moving_to(x1, y1, dragon))
    def moving_to(self, x1, y1, dragon):
        from monsters import Monster
        from bubbles import Bubble
        x0 = self.x
        y0 = self.y
        poplist = [dragon]
        x1 += CELL - self.ico.w//2
        y1 += CELL - self.ico.h//2
        deltax = x1 - x0
        if deltax > -100:
            deltax = -100
        deltay = y1 - y0
        a = - deltay / float(deltax*deltax)
        b = 2 * deltay / float(deltax)
        for x in range(self.x, -self.ico.w, -13):
            x1 = x - x0
            self.move(x, y0 + int((a*x1+b)*x1))
            yield None
            for s in self.touching(10):
                if isinstance(s, Monster):
                    s.argh(poplist)
                elif isinstance(s, Bubble):
                    s.pop(poplist)
        self.kill()

class Fish2(RandomBonus):
    "Rotten Fish. Will blast monsters up to here, so move it around!"
    points = 3000
    nimage = Bonuses.fish2
    def taken1(self, dragons):
        if dragons:
            Megalightning(self.x, self.y, random.choice(dragons))

class Sheep(RandomBonus):
    "Sheep. What a stupid beast!"
    nimage = 'sheep-sm'
    points = 800
    def __init__(self, x, y):
        RandomBonus.__init__(self, x, y)
        if boards.curboard.bonuslevel:
            self.kill()
    def taken1(self, dragons):
        self.points0 = {}
        for p in BubPlayer.PlayerList:
            self.points0[p] = p.points
        BubPlayer.LeaveBonus = self.boardleave()

    def boardleave(self):
        from player import BubPlayer
        BubPlayer.OverridePlayerIcon = images.sprget(self.nimage)
        gamesrv.set_musics([], [])
        images.Snd.Yippee.play()
        slist = []
        ico = images.sprget('sheep-big')
        for p in BubPlayer.PlayerList:
            if p.isplaying() and p.dragons:
                d = random.choice(p.dragons)
                dx = (d.ico.w - ico.w) // 2
                dy = (d.ico.h - ico.h) // 2
                s = ActiveSprite(ico, d.x + dx, d.y + dy)
                dir = getattr(d, 'dir', None)
                if dir not in [-1, 1]:
                    dir = random.choice([-1, 1])
                s.gen.append(s.parabolic([dir, -2.0]))
                slist.append(s)
                for d in p.dragons[:]:
                    d.kill()
        delta = {}
        for p in BubPlayer.PlayerList:
            if p.points or p.isplaying():
                delta[p] = 2 * (self.points0[p] - p.points)
        vy = 0
        while delta or slist:
            ndelta = {}
            for p, dp in delta.items():
                if dp:
                    d1 = max(-250, min(250, dp))
                    p.givepoints(d1)
                    if p.points > 0:
                        ndelta[p] = dp - d1
            delta = ndelta
            images.action(slist)
            slist = [s for s in slist if s.y < boards.bheight]
            yield 1

class Flower(RandomBonus):
    "Flower.  Fire in all directions."
    nimage = 'flower'
    points = 800
    bigbonus = {'multiply': 3}
    def taken(self, dragon):
        dragon.dcap['flower'] += 12
        dragon.carrybonus(self)

class Flower2(TemporaryBonus):
    "Bottom-up Flower.  Turn you upside-down."
    nimage = 'flower2'
    points = 1000
    def __init__(self, *args):
        RandomBonus.__init__(self, *args)
        while not underground(self.x, self.y):
            self.step(0, -CELL)
            if self.y < 0:
                self.kill()
                return
    def faller(self):
        while self.y >= 0:
            if underground(self.x, self.y):
                yield None
                yield None
            else:
                self.move(self.x, (self.y-1) & ~3)
            yield None
        self.kill()
    def taken(self, dragon):
        dragon.dcap['gravity'] *= -1.0
        self.carried(dragon)
    def endaction(self, dragon):
        dragon.dcap['gravity'] *= -1.0

if 'Moebius' in EXTRA_BONUSES:
    class Moebius(RandomBonus):
        "Moebius Band.  Bottom left is top right and bottom right is top left... or vice-versa."
        nimage = 'moebius'
        points = 900
        def taken1(self, dragons):
            BubPlayer.Moebius = not BubPlayer.Moebius

if 'StarBubble' in EXTRA_BONUSES:
    class StarBubble(FireBubble):
        "Star Bubbles. Makes you fire bonus bubbles."
        nimage = 'moebius'
        bubkind = 'StarBubble'
        bubcount = 3
        bigbonus = {'bubcount': 10}


Classes = [c for c in globals().values()
           if type(c)==type(RandomBonus) and issubclass(c, RandomBonus)]
Classes.remove(RandomBonus)
Classes.remove(TemporaryBonus)
Cheat = []
#Classes = [Sheep]  # CHEAT

AllOutcomes = ([(c,) for c in Classes if c is not Fruits] +
               2 * [(MonsterBonus, lvl)
                    for lvl in range(len(Bonuses.monster_bonuses))])

for c in Classes:
    assert (getattr(c, 'points', 0) or 100) in GreenAndBlue.points[0], c

def chooseground(tries=15):
    for i in range(tries):
        x0 = random.randint(2, boards.width-4)
        y0 = random.randint(1, boards.height-3)
        if (' ' == bget(x0,y0+1) == bget(x0+1,y0+1) and
            '#' == bget(x0,y0+2) == bget(x0+1,y0+2)):
            x0 *= CELL
            y0 *= CELL
            for d in BubPlayer.DragonList:
                if abs(d.x-x0) < 3*CELL and abs(d.y-y0) < 3*CELL:
                    break
            else:
                return x0, y0
    else:
        return None, None

def newbonus():
    others = [s for s in images.ActiveSprites if isinstance(s, RandomBonus)]
    if others:
        return
    x, y = chooseground()
    if x is None:
        return
    cls = random.choice(Classes)
    cls(x, y)

##def newbonus():
##    others = [s for s in images.ActiveSprites if isinstance(s, RandomBonus)]
##    if others:
##        return
##    for cls in Classes:
##        x, y = chooseground(200)
##        if x is not None:
##            cls(x, y)

def cheatnew():
    if Cheat:
        x, y = chooseground()
        if x is None:
            return
        cls = random.choice(Cheat)
        if not isinstance(cls, tuple):
            cls = cls,
        else:
            Cheat.remove(cls)
        if len(cls) > 1:
            class C(cls[0]):
                extra_cheat_arg = cls[1]
            cls = (C,)
        cls[0](x, y)
