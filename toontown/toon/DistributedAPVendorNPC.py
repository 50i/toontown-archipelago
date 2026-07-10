from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel, DGG
from direct.interval.IntervalGlobal import LerpPosQuatInterval
from direct.task.Task import Task
from libotp import *
from panda3d.core import Point3, TextNode

from .DistributedNPCToonBase import DistributedNPCToonBase
from toontown.toonbase import ToontownGlobals


AP_VENDOR_MOVIE_CLEAR = 0
AP_VENDOR_MOVIE_START = 1
AP_VENDOR_MOVIE_BUY = 2
AP_VENDOR_MOVIE_CLOSE = 3
AP_VENDOR_MOVIE_NO_MONEY = 4


VENDOR_DATA = {
    0: {
        'walk': "Let me try to sell you this pen.",
        'buy': "I just made my first sale!",
        'close': "Please, come back! I need this job!",
        'pos': (60.92, -36.64, 10.10),
        'h': 139.76,
    },
    1: {
        'walk': "Would you like to open an account?",
        'buy': "Very good, welcome to Toon National Bank!",
        'close': "We offer 5% annual interest!",
        'pos': (26.70, 1.72, -63.24),
        'h': -152.40,
    },
    2: {
        'walk': "Your honor, my client did not kill that Cog.",
        'buy': "Three months in an elder home, that sucks. Lucky for you, I'm well-versed in elder law.",
        'close': "Tell Chuck and Howard I'll be back!",
        'pos': (337.22, -148.84, -43.06),
        'h': 129.40,
    },
    3: {
        'walk': "COGS Inc. just dropped by 40 points. Now's the time to buy!",
        'buy': "You're the majority shareholder now, I hope you don't tank the company!",
        'close': "You're fired!",
        'pos': (-86.60, 21.24, 0.43),
        'h': -76.72,
    },
}


class DistributedAPVendorNPC(DistributedNPCToonBase):
    def __init__(self, cr):
        DistributedNPCToonBase.__init__(self, cr)
        self.vendorType = 0
        self.shopGui = None
        self.price = 0
        self.stoppedLocalAvatar = False
        self.cameraLerp = None

    def setVendorType(self, vendorType):
        self.vendorType = int(vendorType)

    def getVendorType(self):
        return self.vendorType

    def initToonState(self):
        self.setAnimState('neutral', 0.9, None, None)
        data = VENDOR_DATA.get(self.vendorType, VENDOR_DATA[0])
        self.reparentTo(render)
        self.setPosHpr(data['pos'][0], data['pos'][1], data['pos'][2], data['h'], 0, 0)

    def handleCollisionSphereEnter(self, collEntry):
        if self.isBusyWithLocalToon():
            return
        self.setBusyWithLocalToon(True)
        self.sendUpdate('avatarEnter', [])

    def setVendorState(self, mode, avId, price=0):
        isLocalToon = avId == base.localAvatar.doId
        data = VENDOR_DATA.get(self.vendorType, VENDOR_DATA[0])
        self.price = int(price)
        if mode == AP_VENDOR_MOVIE_START:
            self.setChatAbsolute(data['walk'], CFSpeech | CFTimeout)
            if isLocalToon:
                self._beginLocalInteraction(avId)
        elif mode == AP_VENDOR_MOVIE_BUY:
            self.setChatAbsolute(data['buy'], CFSpeech | CFTimeout)
            if isLocalToon:
                self._destroyShopGui()
                self.setBusyWithLocalToon(False)
        elif mode == AP_VENDOR_MOVIE_CLOSE:
            self.setChatAbsolute(data['close'], CFSpeech | CFTimeout)
            if isLocalToon:
                self._destroyShopGui()
                self.setBusyWithLocalToon(False)
        elif mode == AP_VENDOR_MOVIE_NO_MONEY:
            self.setChatAbsolute("You need %s jellybeans for this." % self.price, CFSpeech | CFTimeout)
        elif mode == AP_VENDOR_MOVIE_CLEAR and isLocalToon:
            self._destroyShopGui()
            self.setBusyWithLocalToon(False)

    def _showShopGui(self):
        self._destroyShopGui(releaseAvatar=False, stopCamera=False, cancelTask=False)
        self.shopGui = DirectFrame(
            parent=aspect2dp,
            relief=DGG.RAISED,
            borderWidth=(0.018, 0.018),
            frameColor=(1.0, 0.92, 0.66, 0.97),
            frameSize=(-0.48, 0.48, -0.25, 0.25),
            pos=(0, 0, 0.12),
        )
        DirectFrame(
            parent=self.shopGui,
            relief=DGG.SUNKEN,
            borderWidth=(0.012, 0.012),
            frameColor=(0.45, 0.72, 0.96, 1),
            frameSize=(-0.43, 0.43, -0.18, 0.135),
            pos=(0, 0, -0.01),
        )
        DirectLabel(
            parent=self.shopGui,
            relief=None,
            text=self.getName(),
            text_scale=0.055,
            text_fg=(0.85, 0.12, 0.12, 1),
            text_shadow=(1, 1, 1, 1),
            text_font=ToontownGlobals.getSignFont(),
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.155),
        )
        DirectLabel(
            parent=self.shopGui,
            relief=None,
            text="Random Item\n%s jellybeans" % self.price,
            text_scale=0.045,
            text_fg=(0.05, 0.16, 0.38, 1),
            text_font=ToontownGlobals.getInterfaceFont(),
            text_align=TextNode.ACenter,
            pos=(0, 0, 0.04),
        )
        self._makeButton("Buy", (-0.17, 0, -0.155), self._buy)
        self._makeButton("Close", (0.17, 0, -0.155), self._close)

    def _beginLocalInteraction(self, avId):
        self._destroyShopGui(releaseAvatar=False)
        self._stopLocalAvatar()
        av = base.cr.doId2do.get(avId)
        if av is not None:
            self.setupAvatars(av)
            camera.wrtReparentTo(render)
            self.cameraLerp = LerpPosQuatInterval(
                camera,
                1.0,
                Point3(-5, 9, self.getHeight() - 0.5),
                Point3(-150, -2, 0),
                other=self,
                blendType='easeOut',
                name=self.uniqueName('apVendorLerpCamera'),
            )
            self.cameraLerp.start()
        taskMgr.doMethodLater(1.35, self._popupShopGui, self.uniqueName('popupAPVendorGUI'))

    def _popupShopGui(self, task):
        self._showShopGui()
        return Task.done

    def _makeButton(self, text, pos, command):
        guiButton = loader.loadModel('phase_3/models/gui/quit_button')
        button = DirectButton(
            parent=self.shopGui,
            relief=None,
            image=(guiButton.find('**/QuitBtn_UP'), guiButton.find('**/QuitBtn_DN'), guiButton.find('**/QuitBtn_RLVR')),
            image_scale=(0.72, 1, 1),
            text=text,
            text_fg=(0.05, 0.05, 0.05, 1),
            text_scale=0.052,
            text_pos=(0, -0.018),
            pos=pos,
            scale=0.82,
            command=command,
        )
        guiButton.removeNode()
        return button

    def _buy(self):
        self.sendUpdate('buyRandomItem', [])

    def _close(self):
        self.sendUpdate('closeShop', [])

    def _stopLocalAvatar(self):
        if self.stoppedLocalAvatar:
            return
        place = base.cr.playGame.getPlace()
        if place:
            place.setState('stopped')
            self.stoppedLocalAvatar = True

    def _freeLocalAvatar(self):
        if not self.stoppedLocalAvatar:
            return
        self.stoppedLocalAvatar = False
        base.localAvatar.posCamera(0, 0)
        place = base.cr.playGame.getPlace()
        if place:
            place.setState('walk')

    def _destroyShopGui(self, releaseAvatar=True, stopCamera=True, cancelTask=True):
        if cancelTask:
            taskMgr.remove(self.uniqueName('popupAPVendorGUI'))
        if self.shopGui is not None:
            self.shopGui.destroy()
            self.shopGui = None
        if stopCamera and self.cameraLerp:
            self.cameraLerp.finish()
            self.cameraLerp = None
        if releaseAvatar:
            self._freeLocalAvatar()

    def disable(self):
        self._destroyShopGui()
        DistributedNPCToonBase.disable(self)
