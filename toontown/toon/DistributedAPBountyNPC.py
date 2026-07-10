import math

from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel, DGG
from direct.interval.IntervalGlobal import LerpPosQuatInterval
from direct.task.Task import Task
from libotp import *
from panda3d.core import CardMaker, CollisionBox, CollisionNode, NodePath, Point3, TextNode, Vec4

from .DistributedNPCToonBase import DistributedNPCToonBase
from toontown.archipelago.definitions.bounties import describe_bounty
from toontown.toonbase import ToontownGlobals


AP_BOUNTY_MOVIE_CLEAR = 0
AP_BOUNTY_MOVIE_START = 1
AP_BOUNTY_MOVIE_ACCEPT = 2
AP_BOUNTY_MOVIE_CLOSE = 3
AP_BOUNTY_MOVIE_FULL = 4

BOUNTY_BOARD_BASE_POS = (138.28, 74.48, 5.03)
BOUNTY_BOARD_H = 242.11
BOUNTY_BOARD_BACK_OFFSET = 1.35
BOUNTY_BOARD_WIDTH = 9.0
BOUNTY_BOARD_HEIGHT = 5.0
BOUNTY_BOARD_DEPTH = 0.65

# NPC placement is independent of the board; tune these directly.
BOUNTY_NPC_POS = (134.18, 70.48, 2.53)
BOUNTY_NPC_H = 51.15


class DistributedAPBountyNPC(DistributedNPCToonBase):
    def __init__(self, cr):
        DistributedNPCToonBase.__init__(self, cr)
        self.bountyGui = None
        self.board = None
        self.boardPosterTexts = []
        self.stoppedLocalAvatar = False
        self.cameraLerp = None

    def initToonState(self):
        self.setAnimState('neutral', 0.9, None, None)
        self.reparentTo(render)
        npcX, npcY, npcZ = BOUNTY_NPC_POS
        self.setPosHpr(npcX, npcY, npcZ, BOUNTY_NPC_H, 0, 0)
        self._makeBoard()

    def handleCollisionSphereEnter(self, collEntry):
        if self.isBusyWithLocalToon():
            return
        self.setBusyWithLocalToon(True)
        self.sendUpdate('avatarEnter', [])

    def setBountyState(self, mode, avId, bounties):
        isLocalToon = avId == base.localAvatar.doId
        if mode == AP_BOUNTY_MOVIE_START:
            self.setChatAbsolute("Fresh bounties! Pick one and make it count.", CFSpeech | CFTimeout)
            self._setBoardBounties(bounties)
            if isLocalToon:
                self._beginLocalInteraction(avId, bounties)
        elif mode == AP_BOUNTY_MOVIE_ACCEPT:
            self.setChatAbsolute("Good hunting!", CFSpeech | CFTimeout)
            if isLocalToon:
                self._destroyBountyGui()
                self.setBusyWithLocalToon(False)
        elif mode == AP_BOUNTY_MOVIE_CLOSE:
            self.setChatAbsolute("Come back when you're feeling brave.", CFSpeech | CFTimeout)
            if isLocalToon:
                self._destroyBountyGui()
                self.setBusyWithLocalToon(False)
        elif mode == AP_BOUNTY_MOVIE_FULL:
            self.setChatAbsolute("Finish a bounty first. You've already got four!", CFSpeech | CFTimeout)
            if isLocalToon:
                self._destroyBountyGui()
                self.setBusyWithLocalToon(False)
        elif mode == AP_BOUNTY_MOVIE_CLEAR and isLocalToon:
            self._destroyBountyGui()
            self.setBusyWithLocalToon(False)

    def _beginLocalInteraction(self, avId, bounties):
        self._destroyBountyGui(releaseAvatar=False)
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
                name=self.uniqueName('apBountyLerpCamera'),
            )
            self.cameraLerp.start()
        taskMgr.doMethodLater(1.4, self._popupBountyGui, self.uniqueName('popupAPBountyGUI'), extraArgs=[bounties])

    def _popupBountyGui(self, bounties):
        self._showBountyGui(bounties)
        return Task.done

    def _showBountyGui(self, bounties):
        self._destroyBountyGui(releaseAvatar=False, stopCamera=False, cancelTask=False)
        self.bountyGui = DirectFrame(
            parent=aspect2dp,
            relief=None,
            geom=DGG.getDefaultDialogGeom(),
            geom_scale=(1.45, 1, 1.05),
            geom_color=(0.98, 0.88, 0.55, 1),
            pos=(0, 0, 0.02),
        )
        DirectLabel(
            parent=self.bountyGui,
            relief=None,
            text="Bounty Board",
            text_font=ToontownGlobals.getSignFont(),
            text_scale=0.075,
            text_fg=(0.75, 0.1, 0.08, 1),
            text_shadow=(1, 1, 1, 1),
            pos=(0, 0, 0.39),
        )
        x_positions = (-0.46, 0, 0.46)
        for index, bounty in enumerate(bounties[:3]):
            self._makeBountyCard(bounty, x_positions[index])
        self._makeButton("Close", (0, 0, -0.42), self._close)

    def _makeBountyCard(self, bounty, x):
        bounty_id, objective, progress, reward = describe_bounty(bounty)
        card = DirectFrame(
            parent=self.bountyGui,
            relief=DGG.RAISED,
            borderWidth=(0.012, 0.012),
            frameColor=(1.0, 0.96, 0.76, 1),
            frameSize=(-0.2, 0.2, -0.27, 0.27),
            pos=(x, 0, 0.02),
        )
        DirectLabel(parent=card, relief=None, text=objective, text_wordwrap=8.0, text_scale=0.04,
                    text_font=ToontownGlobals.getInterfaceFont(), text_fg=(0.12, 0.08, 0.02, 1), pos=(0, 0, 0.16))
        DirectLabel(parent=card, relief=None, text="Reward:", text_scale=0.035,
                    text_font=ToontownGlobals.getInterfaceFont(), text_fg=(0.35, 0.08, 0.04, 1), pos=(0, 0, 0.02))
        DirectLabel(parent=card, relief=None, text=reward, text_wordwrap=7.8, text_scale=0.034,
                    text_font=ToontownGlobals.getInterfaceFont(), text_fg=(0.05, 0.18, 0.35, 1), pos=(0, 0, -0.07))
        self._makeButton("Take", (x, 0, -0.27), self._accept, [bounty_id])

    def _makeButton(self, text, pos, command, extraArgs=None):
        guiButton = loader.loadModel('phase_3/models/gui/quit_button')
        button = DirectButton(
            parent=self.bountyGui,
            relief=None,
            image=(guiButton.find('**/QuitBtn_UP'), guiButton.find('**/QuitBtn_DN'), guiButton.find('**/QuitBtn_RLVR')),
            image_scale=(0.72, 1, 1),
            text=text,
            text_fg=(0.05, 0.05, 0.05, 1),
            text_scale=0.045,
            text_pos=(0, -0.015),
            pos=pos,
            scale=0.75,
            command=command,
            extraArgs=extraArgs or [],
        )
        guiButton.removeNode()
        return button

    def _accept(self, bountyId):
        self.sendUpdate('acceptBounty', [int(bountyId)])

    def _close(self):
        self.sendUpdate('closeBountyGui', [])

    def _makeBoard(self):
        if self.board is not None:
            return
        self.board = NodePath(self.uniqueName('apBountyBoard'))
        self.board.reparentTo(render)
        boardX, boardY, boardZ = self._getBoardPosition()
        self.board.setPosHpr(boardX, boardY, boardZ, BOUNTY_BOARD_H, 0, 0)

        halfW = BOUNTY_BOARD_WIDTH / 2.0
        halfH = BOUNTY_BOARD_HEIGHT / 2.0
        halfD = BOUNTY_BOARD_DEPTH / 2.0

        self._makeBoardPanel('apBountyBoardFront', -halfW, halfW, -halfH, halfH, (0, -halfD, 0), (0, 0, 0), (0.04, 0.15, 0.12, 1))
        self._makeBoardPanel('apBountyBoardBack', -halfW, halfW, -halfH, halfH, (0, halfD, 0), (180, 0, 0), (0.38, 0.2, 0.08, 1))
        self._makeBoardPanel('apBountyBoardLeft', -halfD, halfD, -halfH, halfH, (-halfW, 0, 0), (90, 0, 0), (0.43, 0.23, 0.09, 1))
        self._makeBoardPanel('apBountyBoardRight', -halfD, halfD, -halfH, halfH, (halfW, 0, 0), (90, 0, 0), (0.43, 0.23, 0.09, 1))
        self._makeBoardPanel('apBountyBoardTop', -halfW, halfW, -halfD, halfD, (0, 0, halfH), (0, 90, 0), (0.46, 0.25, 0.1, 1))
        self._makeBoardPanel('apBountyBoardBottom', -halfW, halfW, -halfD, halfD, (0, 0, -halfH), (0, 90, 0), (0.32, 0.17, 0.07, 1))

        collNode = CollisionNode(self.uniqueName('apBountyBoardCollision'))
        collNode.addSolid(CollisionBox(Point3(0, 0, 0), halfW, halfD, halfH))
        collNode.setIntoCollideMask(ToontownGlobals.WallBitmask)
        collNode.setFromCollideMask(ToontownGlobals.WallBitmask)
        self.board.attachNewNode(collNode)

        title = TextNode('apBountyBoardTitle')
        title.setText("BOUNTY BOARD")
        title.setAlign(TextNode.ACenter)
        title.setFont(ToontownGlobals.getSignFont())
        title.setTextColor(Vec4(1.0, 0.94, 0.62, 1))
        titlePath = self.board.attachNewNode(title)
        titlePath.setPos(0, -halfD - 0.04, 1.55)
        titlePath.setScale(0.5)

        for index, x in enumerate((-1.75, 0, 1.75)):
            posterMaker = CardMaker('apBountyPoster%d' % index)
            posterMaker.setFrame(-1.05, 1.05, -0.9, 0.9)
            poster = self.board.attachNewNode(posterMaker.generate())
            poster.setPos(x, -halfD - 0.05, -0.22)
            poster.setColor(0.96, 0.89, 0.64, 1)

            text = TextNode('apBountyPosterText%d' % index)
            text.setText("Fresh\nBounty")
            text.setAlign(TextNode.ACenter)
            text.setFont(ToontownGlobals.getInterfaceFont())
            text.setWordwrap(8.5)
            text.setTextColor(Vec4(0.12, 0.08, 0.04, 1))
            textPath = self.board.attachNewNode(text)
            textPath.setPos(x, -halfD - 0.07, -0.05)
            textPath.setScale(0.25)
            self.boardPosterTexts.append(text)

        self._setBoardIdleText()

    def _makeBoardPanel(self, name, left, right, bottom, top, pos, hpr, color):
        maker = CardMaker(name)
        maker.setFrame(left, right, bottom, top)
        panel = self.board.attachNewNode(maker.generate())
        panel.setPos(*pos)
        panel.setHpr(*hpr)
        panel.setColor(*color)
        return panel

    def _setBoardIdleText(self):
        labels = ("Defeat\nCogs", "Random\nRewards", "Ask\nBonnie")
        for index, text in enumerate(self.boardPosterTexts):
            text.setText(labels[index])

    def _setBoardBounties(self, bounties):
        if not self.boardPosterTexts:
            return
        for index, text in enumerate(self.boardPosterTexts):
            if index >= len(bounties):
                text.setText("")
                continue
            _bountyId, objective, progress, reward = describe_bounty(bounties[index])
            text.setText("%s\n%s\n%s" % (objective, progress, reward))

    def _getBoardPosition(self):
        radians = math.radians(BOUNTY_BOARD_H)
        localX = 0
        localY = BOUNTY_BOARD_BACK_OFFSET
        worldX = BOUNTY_BOARD_BASE_POS[0] + (localX * math.cos(radians)) - (localY * math.sin(radians))
        worldY = BOUNTY_BOARD_BASE_POS[1] + (localX * math.sin(radians)) + (localY * math.cos(radians))
        return worldX, worldY, BOUNTY_BOARD_BASE_POS[2]

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

    def _destroyBountyGui(self, releaseAvatar=True, stopCamera=True, cancelTask=True):
        if cancelTask:
            taskMgr.remove(self.uniqueName('popupAPBountyGUI'))
        if self.bountyGui is not None:
            self.bountyGui.destroy()
            self.bountyGui = None
        if stopCamera and self.cameraLerp:
            self.cameraLerp.finish()
            self.cameraLerp = None
        if releaseAvatar:
            self._freeLocalAvatar()

    def disable(self):
        self._destroyBountyGui()
        if self.board is not None:
            self.board.removeNode()
            self.board = None
        DistributedNPCToonBase.disable(self)