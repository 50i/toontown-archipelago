from toontown.toonbase.ToonBaseGlobal import *
from panda3d.core import *
from panda3d.toontown import *
from toontown.toonbase.ToontownGlobals import *
import random
from direct.distributed import DistributedObject
from direct.directnotify import DirectNotifyGlobal
from direct.actor import Actor
from direct.gui.DirectGui import DirectButton
from . import ToonInteriorColors
from toontown.hood import ZoneUtil
from toontown.archipelago.util.useless_marks import get_marked_hoods, is_hood_marked, set_marked_hoods

class DistributedPetshopInterior(DistributedObject.DistributedObject):

    def __init__(self, cr):
        DistributedObject.DistributedObject.__init__(self, cr)
        self.dnaStore = cr.playGame.dnaStore
        self.uselessPetShopButton = None

    def generate(self):
        DistributedObject.DistributedObject.generate(self)

    def announceGenerate(self):
        DistributedObject.DistributedObject.announceGenerate(self)
        self.setup()

    def randomDNAItem(self, category, findFunc):
        codeCount = self.dnaStore.getNumCatalogCodes(category)
        index = self.randomGenerator.randint(0, codeCount - 1)
        code = self.dnaStore.getCatalogCode(category, index)
        return findFunc(code)

    def replaceRandomInModel(self, model):
        baseTag = 'random_'
        npc = model.findAllMatches('**/' + baseTag + '???_*')
        for i in range(npc.getNumPaths()):
            np = npc.getPath(i)
            name = np.getName()
            b = len(baseTag)
            category = name[b + 4:]
            key1 = name[b]
            key2 = name[b + 1]
            if key1 == 'm':
                model = self.randomDNAItem(category, self.dnaStore.findNode)
                newNP = model.copyTo(np)
                if key2 == 'r':
                    self.replaceRandomInModel(newNP)
            elif key1 == 't':
                texture = self.randomDNAItem(category, self.dnaStore.findTexture)
                np.setTexture(texture, 100)
                newNP = np
            if key2 == 'c':
                if category == 'TI_wallpaper' or category == 'TI_wallpaper_border':
                    self.randomGenerator.seed(self.zoneId)
                    newNP.setColorScale(self.randomGenerator.choice(self.colors[category]))
                else:
                    newNP.setColorScale(self.randomGenerator.choice(self.colors[category]))

    def setZoneIdAndBlock(self, zoneId, block):
        self.zoneId = zoneId
        self.block = block

    def chooseDoor(self):
        doorModelName = 'door_double_round_ul'
        if doorModelName[-1:] == 'r':
            doorModelName = doorModelName[:-1] + 'l'
        else:
            doorModelName = doorModelName[:-1] + 'r'
        door = self.dnaStore.findNode(doorModelName)
        return door

    def setup(self):
        self.dnaStore = base.cr.playGame.dnaStore
        self.randomGenerator = random.Random()
        self.randomGenerator.seed(self.zoneId)
        self.interior = loader.loadModel('phase_4/models/modules/PetShopInterior')
        self.interior.reparentTo(render)
        self.fish = Actor.Actor('phase_4/models/props/interiorfish-zero', {'swim': 'phase_4/models/props/interiorfish-swim'})
        self.fish.reparentTo(self.interior)
        self.fish.setColorScale(0.8, 0.9, 1, 0.8)
        self.fish.setScale(0.8)
        self.fish.setPos(0, 6, -4)
        self.fish.setPlayRate(0.7, 'swim')
        self.fish.loop('swim')
        hoodId = ZoneUtil.getCanonicalHoodId(self.zoneId)
        self.colors = ToonInteriorColors.colors[hoodId]
        self.replaceRandomInModel(self.interior)
        door = self.chooseDoor()
        doorOrigin = render.find('**/door_origin;+s')
        doorNP = door.copyTo(doorOrigin)
        doorOrigin.setScale(0.8, 0.8, 0.8)
        doorOrigin.setPos(doorOrigin, 0, -0.25, 0)
        doorColor = self.randomGenerator.choice(self.colors['TI_door'])
        DNADoor.setupDoor(doorNP, self.interior, doorOrigin, self.dnaStore, str(self.block), doorColor)
        doorFrame = doorNP.find('door_*_flat')
        doorFrame.wrtReparentTo(self.interior)
        doorFrame.setColor(doorColor)
        del self.colors
        del self.dnaStore
        del self.randomGenerator
        self.interior.flattenMedium()
        self._createUselessPetShopButton(hoodId)

    def _createUselessPetShopButton(self, hoodId):
        """Offer a local tracker control for pet shops with no useful checks."""
        self.uselessPetShopHoodId = hoodId
        isMarkedUseless = is_hood_marked('useless-pet-shop-hoods', hoodId)
        self.uselessPetShopButton = DirectButton(
            parent=base.a2dBottomLeft,
            relief='raised',
            frameColor=(0.35, 0.55, 0.35, 1) if isMarkedUseless else (0.8, 0.25, 0.25, 1),
            frameSize=(-2.0, 2.0, -0.85, 0.85),
            scale=0.15,
            pos=(0.34, 0, 0.48),
            text='Unmark\nDoodles' if isMarkedUseless else 'Mark Doodles\nUseless',
            text_scale=0.22,
            text_wordwrap=9,
            text_align=TextNode.ACenter,
            command=self.unmarkPetShopUseless if isMarkedUseless else self.markPetShopUseless,
        )

    def markPetShopUseless(self):
        markedHoods = get_marked_hoods('useless-pet-shop-hoods')
        if self.uselessPetShopHoodId not in markedHoods:
            markedHoods.append(self.uselessPetShopHoodId)
            set_marked_hoods('useless-pet-shop-hoods', markedHoods)
            # MapPage's refresh callback needs no event arguments.
            messenger.send('petshop-marked-useless')

        if self.uselessPetShopButton:
            self.uselessPetShopButton.destroy()
            self.uselessPetShopButton = None
        self._createUselessPetShopButton(self.uselessPetShopHoodId)

    def unmarkPetShopUseless(self):
        markedHoods = get_marked_hoods('useless-pet-shop-hoods')
        if self.uselessPetShopHoodId in markedHoods:
            markedHoods.remove(self.uselessPetShopHoodId)
            set_marked_hoods('useless-pet-shop-hoods', markedHoods)
            messenger.send('petshop-marked-useless')

        if self.uselessPetShopButton:
            self.uselessPetShopButton.destroy()
            self.uselessPetShopButton = None
        self._createUselessPetShopButton(self.uselessPetShopHoodId)

    def disable(self):
        if self.uselessPetShopButton:
            self.uselessPetShopButton.destroy()
            self.uselessPetShopButton = None
        self.fish.stop()
        self.fish.cleanup()
        del self.fish
        self.interior.removeNode()
        del self.interior
        DistributedObject.DistributedObject.disable(self)
