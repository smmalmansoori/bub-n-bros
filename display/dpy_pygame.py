
 ################################################
##     pygame-based implementation of xshm     ##
################################################

import os
import pygame
from pygame.locals import *
from modes import KeyPressed, KeyReleased


class Display:
    
    def __init__(self, width, height, title):
        # Initialize pygame
        pygame.init()

        # Set the display mode
        winstyle = HWSURFACE  # |FULLSCREEN
        bestdepth = pygame.display.mode_ok((width, height), winstyle, 32)
        self.screen = pygame.display.set_mode((width, height),
                                              winstyle, bestdepth)
        self.offscreen = pygame.Surface((width, height))
        #decorate the game window
        pygame.display.set_caption(title)
        #pygame.mouse.set_visible(0)
        self.tbcache = None, None
        self.events_key = []
        self.events_mouse = []
        self.prevposition = None
        EVENT_HANDLERS[KEYDOWN] = self.keydown_handler
        EVENT_HANDLERS[KEYUP] = self.keyup_handler
        EVENT_HANDLERS[MOUSEBUTTONDOWN] = self.mousebuttondown_handler

    def keydown_handler(self, e):
        self.events_key.append((e.key, KeyPressed))
        del self.events_key[:-16]

    def keyup_handler(self, e):
        self.events_key.append((e.key, KeyReleased))
        del self.events_key[:-16]

    def mousebuttondown_handler(self, e):
        self.events_mouse.append(e.pos)
        del self.events_mouse[:-8]

    def pixmap(self, w, h, data, colorkey=-1):
        img = pygame.image.fromstring(data, (w, h), "RGB").convert()
        if colorkey >= 0:
            r = colorkey & 0xFF
            g = (colorkey >> 8) & 0xFF
            b = (colorkey >> 16) & 0xFF
            img.set_colorkey([r, g, b], RLEACCEL)
        return img

##    def vflipppm(self, img):
##        w, h = img.get_size()
##        colorkey = img.get_colorkey()
##        data = pygame.image.tostring(img, "RGB", 1)
##        flipimg = pygame.image.fromstring(data, (w, h), "RGB")
##        flipimg.set_colorkey(colorkey, RLEACCEL)
##        return flipimg, h

    def getppm(self, rect, bkgnd=None):
        if bkgnd is None:
            bkgnd = pygame.Surface(rect[2:])
        bkgnd.blit(self.offscreen, (0, 0), Rect(rect))
        return bkgnd

    def putppm(self, x, y, bitmap, rect=None):
        if rect:
            self.offscreen.blit(bitmap, (x, y), rect)
        else:
            self.offscreen.blit(bitmap, (x, y))

    def flip(self):
        self.screen.blit(self.offscreen, (0, 0))
        pygame.display.flip()
        events_dispatch()

    def close(self):
        pygame.display.quit()

    def clear(self):
        self.offscreen.fill([0,0,0,])

    def events_poll(self):
        while 1:
            e = pygame.event.poll()
            if e.type == NOEVENT:
                break
            elif e.type == KEYDOWN:
                self.events_key.append((e.key, KeyPressed))
                del self.events_key[:-16]
            elif e.type == KEYUP:
                self.events_key.append((e.key, KeyReleased))
                del self.events_key[:-16]
            elif e.type == MOUSEBUTTONDOWN:
                self.events_mouse.append(e.pos)
                del self.events_mouse[:-8]
            elif e.type == ENDMUSICEVENT:
                self.next_music()
            elif e.type == QUIT:
                raise SystemExit

    def keyevents(self):
        events_dispatch()
        events = self.events_key
        self.events_key = []
        return events

    def pointermotion(self):
        position = pygame.mouse.get_pos()
        if position != self.prevposition:
            self.prevposition = position
            return position
        else:
            return None

    def mouseevents(self):
        events_dispatch()
        events = self.events_mouse
        self.events_mouse = []
        return events

    def selectlist(self):
        return []

    def taskbar(self, (x, y, w, h)):
        tbs, tbh = self.tbcache
        if tbh != h:
            tbs = pygame.Surface((32, h)).convert_alpha()
            alpha_f = 256.0 / h
            for j in range(h):
                tbs.fill((128, 128, 255, int(j*alpha_f)),
                         (0, j, 32, 1))
            self.tbcache = tbs, h
        for i in range(x, x+w, 32):
            dw = x+w-i
            if dw < 32:
                self.offscreen.blit(tbs, (i, y), (0, 0, dw, h))
            else:
                self.offscreen.blit(tbs, (i, y))


def quit_handler(e):
    raise SystemExit

EVENT_HANDLERS = {
    QUIT: quit_handler,
    }

def events_dispatch(handlers = EVENT_HANDLERS):
    while 1:
        e = pygame.event.poll()
        if e.type == NOEVENT:
            break
        elif handlers.has_key(e.type):
            handlers[e.type](e)