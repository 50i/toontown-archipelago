from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel, DGG
from panda3d.core import TextNode

from .ShtikerPage import ShtikerPage
from toontown.archipelago.definitions.bounties import MAX_ACTIVE_BOUNTIES, describe_bounty
from toontown.toonbase import TTLocalizer, ToontownGlobals


class BountyPage(ShtikerPage):
    def __init__(self):
        ShtikerPage.__init__(self)
        self.cards = []
        self.emptyLabel = None

    def load(self):
        self.title = DirectLabel(
            parent=self,
            relief=None,
            text=TTLocalizer.BountyPageTitle,
            text_scale=0.12,
            text_font=ToontownGlobals.getSignFont(),
            text_fg=(0.75, 0.08, 0.05, 1),
            text_shadow=(1, 1, 1, 1),
            pos=(0, 0, 0.6),
        )
        self.emptyLabel = DirectLabel(
            parent=self,
            relief=None,
            text=TTLocalizer.BountyPageNoBounties,
            text_scale=0.07,
            text_font=ToontownGlobals.getInterfaceFont(),
            text_fg=(0.15, 0.1, 0.05, 1),
            pos=(0, 0, 0.1),
        )
        self._buildCards()
        self._refresh()

    def unload(self):
        self.ignore('ap-bounties-updated')
        for card in self.cards:
            card.destroy()
        self.cards = []
        if self.emptyLabel:
            self.emptyLabel.destroy()
            self.emptyLabel = None
        self.title.destroy()
        ShtikerPage.unload(self)

    def enter(self):
        ShtikerPage.enter(self)
        self.accept('ap-bounties-updated', self._refresh)
        self._refresh()

    def exit(self):
        self.ignore('ap-bounties-updated')
        ShtikerPage.exit(self)

    def _buildCards(self):
        positions = ((0, 0.12), (0, 0.12), (0, 0.12), (0, 0.12))
        for index in range(MAX_ACTIVE_BOUNTIES):
            x, z = positions[index]
            card = DirectFrame(
                parent=self,
                relief=DGG.RAISED,
                borderWidth=(0.012, 0.012),
                frameColor=(1.0, 0.95, 0.72, 1),
                frameSize=(-0.42, 0.42, -0.27, 0.19),
                pos=(x, 0, z),
            )
            card.objective = DirectLabel(parent=card, relief=None, text='', text_wordwrap=10.5,
                                         text_scale=0.038, text_font=ToontownGlobals.getInterfaceFont(),
                                         text_align=TextNode.ACenter, text_fg=(0.12, 0.08, 0.03, 1),
                                         pos=(0, 0, 0.075))
            card.progress = DirectLabel(parent=card, relief=None, text='', text_scale=0.042,
                                        text_font=ToontownGlobals.getSignFont(),
                                        text_fg=(0.72, 0.08, 0.05, 1), pos=(0, 0, -0.025))
            card.reward = DirectLabel(parent=card, relief=None, text='', text_wordwrap=10.5,
                                      text_scale=0.031, text_font=ToontownGlobals.getInterfaceFont(),
                                      text_fg=(0.05, 0.18, 0.35, 1), pos=(0, 0, -0.105))
            card.deleteButton = self._makeButton(card, "Delete", (0, 0, -0.205), self._deleteBounty)
            self.cards.append(card)

    def _refresh(self):
        if not hasattr(base, 'localAvatar'):
            return
        bounties = base.localAvatar.getAPBounties()
        hasBounties = bool(bounties)
        if self.emptyLabel:
            if hasBounties:
                self.emptyLabel.hide()
            else:
                self.emptyLabel.show()
        for index, card in enumerate(self.cards):
            if index >= len(bounties):
                card.hide()
                continue
            _bountyId, objective, progress, reward = describe_bounty(bounties[index])
            card.bountyId = _bountyId
            card.objective['text'] = objective
            card.progress['text'] = progress
            card.reward['text'] = 'Reward: %s' % reward
            card.show()

    def _makeButton(self, parent, text, pos, command):
        guiButton = loader.loadModel('phase_3/models/gui/quit_button')
        button = DirectButton(
            parent=parent,
            relief=None,
            image=(guiButton.find('**/QuitBtn_UP'), guiButton.find('**/QuitBtn_DN'), guiButton.find('**/QuitBtn_RLVR')),
            image_scale=(0.62, 1, 0.78),
            text=text,
            text_fg=(0.05, 0.05, 0.05, 1),
            text_scale=0.035,
            text_pos=(0, -0.012),
            pos=pos,
            scale=0.62,
            command=command,
            extraArgs=[parent],
        )
        guiButton.removeNode()
        return button

    def _deleteBounty(self, card):
        bountyId = getattr(card, 'bountyId', 0)
        if bountyId and hasattr(base, 'localAvatar'):
            base.localAvatar.d_requestDeleteAPBounty(bountyId)
